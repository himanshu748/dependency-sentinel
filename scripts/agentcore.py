"""Reproducible ARM64 zip packaging and on-demand AgentCore deployment.

Run with backend/.venv/bin/python scripts/agentcore.py package|deploy|status.
Deployment creates a private S3 bucket, one scoped execution role, and one IAM-authenticated
runtime. Model probes and deployment require --allow-paid. State is saved under .agentcore/.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
NAME = ROOT.name.replace("-", "_") + "_advisor"
REGION = "us-east-1"
MODEL = "amazon.nova-micro-v1:0"
QUOTA_CODE = "L-D2912E70"
BUILD = ROOT / ".agentcore"
STATE = BUILD / "deployment.json"
PROVIDER = "bedrock"
BASE_URL = None
SECRET_ARN = None


def external_preflight(session, account, *, allow_inference=False):
    """Verify an external provider without requiring Bedrock model access."""
    sys.path.insert(0, str(ROOT / "backend"))
    from app.agent.provider import validate_provider_configuration
    from app.config import Settings

    settings = Settings(
        _env_file=None,
        fixture_mode=False,
        agentcore_runtime_arn=None,
        llm_provider=PROVIDER,
        llm_model_id=MODEL,
        llm_base_url=BASE_URL,
        llm_api_key="metadata-validation-placeholder",
    )
    validate_provider_configuration(settings)
    prefix = f"arn:aws:secretsmanager:{REGION}:{account}:secret:"
    if not SECRET_ARN or not SECRET_ARN.startswith(prefix):
        raise SystemExit("Supply a model credential secret ARN in this account and region")
    if not BASE_URL.startswith("https://"):
        raise SystemExit("Cloud runtimes require an HTTPS provider endpoint")
    secrets = session.client("secretsmanager")
    metadata = secrets.describe_secret(SecretId=SECRET_ARN)
    if metadata.get("DeletedDate"):
        raise SystemExit("Model credential is scheduled for deletion")
    if metadata.get("KmsKeyId") not in {None, "alias/aws/secretsmanager"}:
        raise SystemExit("This recipe requires the AWS-managed Secrets Manager encryption key")
    session.client("bedrock-agentcore-control").list_agent_runtimes(maxResults=1)
    result = {
        "account": account,
        "model": MODEL,
        "provider": PROVIDER,
        "region": REGION,
        "inference_verified": False,
        "bedrock_model_access_required": False,
    }
    if not allow_inference:
        return result
    # Secret values stay in memory and never enter state, command output or runtime env.
    from openai import OpenAI, OpenAIError

    key = os.getenv("LLM_API_KEY")
    if not isinstance(key, str) or not key.strip():
        raise SystemExit(
            "Resolve the model credential into LLM_API_KEY with asm-exec before a paid probe"
        )
    try:
        with OpenAI(base_url=BASE_URL, api_key=key.strip(), max_retries=0, timeout=30) as client:
            probe = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": "Reply with OK."}],
                max_tokens=128,
                temperature=0,
            )
        if not probe.choices or not probe.choices[0].message.content:
            raise SystemExit("External provider returned no text")
    except (OpenAIError, ValueError) as error:
        raise SystemExit(
            f"External inference preflight failed ({type(error).__name__}); "
            "no deployment resources were created"
        ) from None
    return {
        **result,
        "inference_verified": True,
        "usage": probe.usage.model_dump() if probe.usage else {},
    }


def package():
    BUILD.mkdir(exist_ok=True)
    requirements = BUILD / "requirements.txt"
    subprocess.run(
        [
            "uv",
            "export",
            "--frozen",
            "--no-dev",
            "--no-emit-project",
            "--format",
            "requirements-txt",
            "--output-file",
            str(requirements),
        ],
        cwd=ROOT / "backend",
        check=True,
        stdout=subprocess.DEVNULL,
    )
    with tempfile.TemporaryDirectory(prefix="agentcore-package-") as temporary:
        target = Path(temporary)
        subprocess.run(
            [
                "uv",
                "pip",
                "install",
                "--python-platform",
                "aarch64-manylinux2014",
                "--python-version",
                "3.12",
                "--target",
                str(target),
                "--only-binary=:all:",
                "-r",
                str(requirements),
            ],
            check=True,
        )
        shutil.copytree(
            ROOT / "backend" / "app",
            target / "app",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        shutil.copy(ROOT / "backend" / "agentcore_main.py", target)
        archive = BUILD / "deployment.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
            for path in sorted(target.rglob("*")):
                if path.is_file() and "__pycache__" not in path.parts:
                    info = zipfile.ZipInfo.from_file(path, path.relative_to(target))
                    info.external_attr = 0o100644 << 16
                    info.compress_type = zipfile.ZIP_DEFLATED
                    bundle.writestr(info, path.read_bytes())
    print(json.dumps({"archive": str(archive), "bytes": archive.stat().st_size}))


def preflight(session=None, *, allow_inference=False):
    """Fail before provisioning when account/model inference is unavailable.

    Default: read-only metadata, never inference. The optional paid probe is
    bounded to eight output tokens and never retried. Passing metadata checks
    does not prove inference works or that credits cover charges.
    """
    session = session or boto3.Session(region_name=REGION)
    account = session.client("sts").get_caller_identity()["Account"]
    if PROVIDER == "openai-compatible":
        return external_preflight(session, account, allow_inference=allow_inference)
    availability = session.client("bedrock").get_foundation_model_availability(modelId=MODEL)
    if (
        availability.get("authorizationStatus") != "AUTHORIZED"
        or availability.get("regionAvailability") != "AVAILABLE"
        or availability.get("entitlementAvailability") != "AVAILABLE"
        or availability.get("agreementAvailability", {}).get("status") != "AVAILABLE"
    ):
        raise SystemExit("Bedrock model is not available; no deployment resources were created")
    quota = session.client("service-quotas").get_service_quota(
        ServiceCode="bedrock", QuotaCode=QUOTA_CODE
    )["Quota"]
    if quota["Value"] <= 0:
        raise SystemExit(
            f"Configured model quota is zero in {REGION} ({QUOTA_CODE}). "
            "Ask AWS Support to restore inference quota; no deployment resources were created."
        )
    result = {
        "account": account,
        "model": MODEL,
        "region": REGION,
        "quota_code": QUOTA_CODE,
        "quota_value": quota["Value"],
        "inference_verified": False,
    }
    if not allow_inference:
        return result
    runtime = session.client(
        "bedrock-runtime",
        config=Config(
            connect_timeout=10,
            read_timeout=30,
            retries={"total_max_attempts": 1},
        ),
    )
    try:
        probe = runtime.converse(
            modelId=MODEL,
            messages=[{"role": "user", "content": [{"text": "Reply with OK."}]}],
            inferenceConfig={"maxTokens": 8, "temperature": 0},
        )
    except ClientError as error:
        code = error.response["Error"]["Code"]
        raise SystemExit(
            f"Bedrock inference preflight failed ({code}); no deployment resources were created"
        ) from error
    content = probe.get("output", {}).get("message", {}).get("content", [])
    if not any(block.get("text", "").strip() for block in content):
        raise SystemExit("Bedrock returned no text; no deployment resources were created")
    return {**result, "inference_verified": True, "usage": probe.get("usage", {})}


def deploy(*, allow_paid=False):
    if not allow_paid:
        raise SystemExit("Deployment requires --allow-paid; credits are not a billing hard cap")
    archive = BUILD / "deployment.zip"
    if not archive.exists():
        raise SystemExit("Run package first")
    if STATE.exists():
        raise SystemExit("Deployment already recorded; inspect status before changing it")
    session = boto3.Session(region_name=REGION)
    account = preflight(session, allow_inference=True)["account"]
    bucket = f"afh-{ROOT.name}-{account}-{REGION}"
    role_name = f"AFH-{ROOT.name}-AgentCore"
    s3, iam = session.client("s3"), session.client("iam")
    try:
        s3.create_bucket(Bucket=bucket)
    except ClientError as error:
        if error.response["Error"]["Code"] != "BucketAlreadyOwnedByYou":
            raise
    s3.put_public_access_block(
        Bucket=bucket,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        },
    )
    s3.put_bucket_encryption(
        Bucket=bucket,
        ServerSideEncryptionConfiguration={
            "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
        },
    )
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    key = f"code/{digest}.zip"
    s3.upload_file(str(archive), bucket, key, ExtraArgs={"ExpectedBucketOwner": account})
    trust = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
                "Action": "sts:AssumeRole",
                "Condition": {
                    "StringEquals": {"aws:SourceAccount": account},
                    "ArnLike": {"aws:SourceArn": f"arn:aws:bedrock-agentcore:{REGION}:{account}:*"},
                },
            }
        ],
    }
    try:
        role = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust),
            Tags=[{"Key": "Project", "Value": ROOT.name}],
        )["Role"]
    except iam.exceptions.EntityAlreadyExistsException:
        role = iam.get_role(RoleName=role_name)["Role"]
        iam.update_assume_role_policy(RoleName=role_name, PolicyDocument=json.dumps(trust))
    log_arn = f"arn:aws:logs:{REGION}:{account}:log-group:/aws/bedrock-agentcore/runtimes/{NAME}-*"
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["s3:GetObject"],
                "Resource": f"arn:aws:s3:::{bucket}/{key}",
            },
            {
                "Effect": "Allow",
                "Action": ["s3:ListBucket"],
                "Resource": f"arn:aws:s3:::{bucket}",
            },
            {
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:DescribeLogStreams",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                    "logs:PutResourcePolicy",
                ],
                "Resource": [log_arn, log_arn + ":*"],
            },
            {
                "Effect": "Allow",
                "Action": ["logs:DescribeLogGroups"],
                "Resource": f"arn:aws:logs:{REGION}:{account}:log-group:*",
            },
            {
                "Effect": "Allow",
                "Action": [
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                ],
                "Resource": f"arn:aws:bedrock:{REGION}::foundation-model/{MODEL}",
            },
        ],
    }
    if PROVIDER == "openai-compatible":
        policy["Statement"][-1] = {
            "Effect": "Allow",
            "Action": ["secretsmanager:GetSecretValue"],
            "Resource": SECRET_ARN,
        }
    iam.put_role_policy(
        RoleName=role_name,
        PolicyName="AdvisoryRuntime",
        PolicyDocument=json.dumps(policy),
    )
    state = {
        "name": NAME,
        "region": REGION,
        "bucket": bucket,
        "key": key,
        "role_name": role_name,
        "model": MODEL,
        "sha256": digest,
        "provider": PROVIDER,
    }
    STATE.write_text(json.dumps(state, indent=2) + "\n")
    time.sleep(12)  # bounded IAM propagation delay
    control = session.client("bedrock-agentcore-control")
    runtime_environment = {
        "AGENT_FIXTURE_MODE": "false",
        "AWS_RETRY_MODE": "standard",
        "AWS_MAX_ATTEMPTS": "2",
        "LLM_PROVIDER": PROVIDER,
    }
    if PROVIDER == "openai-compatible":
        runtime_environment.update(
            {
                "LLM_MODEL_ID": MODEL,
                "LLM_BASE_URL": BASE_URL,
                "LLM_API_KEY_SECRET_ARN": SECRET_ARN,
            }
        )
    else:
        runtime_environment["BEDROCK_MODEL_ID"] = MODEL
    response = control.create_agent_runtime(
        agentRuntimeName=NAME,
        agentRuntimeArtifact={
            "codeConfiguration": {
                "code": {"s3": {"bucket": bucket, "prefix": key}},
                "runtime": "PYTHON_3_12",
                "entryPoint": ["agentcore_main.py"],
            }
        },
        roleArn=role["Arn"],
        networkConfiguration={"networkMode": "PUBLIC"},
        protocolConfiguration={"serverProtocol": "HTTP"},
        lifecycleConfiguration={"idleRuntimeSessionTimeout": 60, "maxLifetime": 300},
        environmentVariables=runtime_environment,
        tags={"Project": ROOT.name, "Event": "AgentsForHumans"},
    )
    state.update({"arn": response["agentRuntimeArn"], "id": response["agentRuntimeId"]})
    STATE.write_text(json.dumps(state, indent=2) + "\n")
    print(json.dumps(state, indent=2))


def status():
    state = json.loads(STATE.read_text())
    control = boto3.client("bedrock-agentcore-control", region_name=REGION)
    result = control.get_agent_runtime(agentRuntimeId=state["id"])
    print(
        json.dumps(
            {
                key: result.get(key)
                for key in (
                    "agentRuntimeArn",
                    "status",
                    "failureReason",
                    "agentRuntimeVersion",
                )
            }
        )
    )
    endpoints = control.list_agent_runtime_endpoints(agentRuntimeId=state["id"])
    print(json.dumps(endpoints.get("runtimeEndpoints", []), default=str))
    # Status must remain read-only. Retention is a separate explicit operation.


def set_log_retention():
    state = json.loads(STATE.read_text())
    logs = boto3.client("logs", region_name=state["region"])
    for group in logs.describe_log_groups(
        logGroupNamePrefix=f"/aws/bedrock-agentcore/runtimes/{state['id']}"
    )["logGroups"]:
        logs.put_retention_policy(logGroupName=group["logGroupName"], retentionInDays=7)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=["package", "preflight", "deploy", "status", "set-log-retention"],
    )
    parser.add_argument(
        "--allow-paid",
        action="store_true",
        help="Opt in to a bounded inference probe or deployment; not a spending cap",
    )
    parser.add_argument("--model-id", help="Model ID on the explicitly selected provider")
    parser.add_argument("--provider", choices=["bedrock", "openai-compatible"], default="bedrock")
    parser.add_argument("--base-url", help="HTTPS OpenAI-compatible provider base URL")
    parser.add_argument("--secret-arn", help="Plain-text API key stored in AWS Secrets Manager")
    parser.add_argument("--quota-code", help="Verified service quota code for the chosen model")
    load_dotenv(ROOT / "backend" / ".env", override=False)
    args = parser.parse_args()
    PROVIDER = args.provider
    BASE_URL = args.base_url
    SECRET_ARN = args.secret_arn
    if (
        args.command in {"preflight", "deploy"}
        and PROVIDER == "openai-compatible"
        and not all((args.model_id, args.base_url, args.secret_arn))
    ):
        parser.error("External runtime requires --model-id, --base-url and --secret-arn")
    if os.environ.get("AWS_PROFILE") == "":
        del os.environ["AWS_PROFILE"]
    MODEL = args.model_id or os.getenv("BEDROCK_MODEL_ID") or MODEL
    if args.command in {"preflight", "deploy"} and PROVIDER == "bedrock":
        if not re.fullmatch(r"[a-z0-9][a-z0-9.-]*(?::[0-9]+)?", MODEL) or MODEL.startswith(
            ("us.", "eu.", "apac.", "global.")
        ):
            parser.error(
                "This deployment recipe accepts direct foundation model IDs only; "
                "use direct Bedrock mode for inference profiles"
            )
        if MODEL != "amazon.nova-micro-v1:0" and not args.quota_code:
            parser.error(
                "Supply --quota-code for the selected model; "
                "the Nova Micro quota must not be reused"
            )
    QUOTA_CODE = args.quota_code or QUOTA_CODE
    {
        "package": package,
        "preflight": lambda: print(json.dumps(preflight(allow_inference=args.allow_paid))),
        "deploy": lambda: deploy(allow_paid=args.allow_paid),
        "status": status,
        "set-log-retention": set_log_retention,
    }[args.command]()
