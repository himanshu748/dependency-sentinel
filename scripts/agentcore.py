"""Reproducible ARM64 zip packaging and on-demand AgentCore deployment.

Run with backend/.venv/bin/python scripts/agentcore.py package|deploy|status.
Deployment creates a private S3 bucket, one scoped execution role, and one IAM-authenticated
runtime. No model is called until an explicit invocation. State is saved under .agentcore/.
"""

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
import time
import zipfile
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

ROOT = Path(__file__).resolve().parents[1]
NAME = ROOT.name.replace("-", "_") + "_advisor"
REGION = "us-east-1"
MODEL = "amazon.nova-micro-v1:0"
BUILD = ROOT / ".agentcore"
STATE = BUILD / "deployment.json"


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


def deploy():
    archive = BUILD / "deployment.zip"
    if not archive.exists():
        raise SystemExit("Run package first")
    if STATE.exists():
        raise SystemExit("Deployment already recorded; inspect status before changing it")
    session = boto3.Session(region_name=REGION)
    account = session.client("sts").get_caller_identity()["Account"]
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
            {"Effect": "Allow", "Action": ["s3:ListBucket"], "Resource": f"arn:aws:s3:::{bucket}"},
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
                "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
                "Resource": f"arn:aws:bedrock:{REGION}::foundation-model/{MODEL}",
            },
        ],
    }
    iam.put_role_policy(
        RoleName=role_name, PolicyName="AdvisoryRuntime", PolicyDocument=json.dumps(policy)
    )
    state = {
        "name": NAME,
        "region": REGION,
        "bucket": bucket,
        "key": key,
        "role_name": role_name,
        "model": MODEL,
        "sha256": digest,
    }
    STATE.write_text(json.dumps(state, indent=2) + "\n")
    time.sleep(12)  # bounded IAM propagation delay
    control = session.client("bedrock-agentcore-control")
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
        environmentVariables={
            "BEDROCK_MODEL_ID": MODEL,
            "AGENT_FIXTURE_MODE": "false",
            "AWS_RETRY_MODE": "standard",
            "AWS_MAX_ATTEMPTS": "2",
        },
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
                for key in ("agentRuntimeArn", "status", "failureReason", "agentRuntimeVersion")
            }
        )
    )
    endpoints = control.list_agent_runtime_endpoints(agentRuntimeId=state["id"])
    print(json.dumps(endpoints.get("runtimeEndpoints", []), default=str))
    logs = boto3.client("logs", region_name=REGION)
    for group in logs.describe_log_groups(
        logGroupNamePrefix=f"/aws/bedrock-agentcore/runtimes/{state['id']}"
    )["logGroups"]:
        logs.put_retention_policy(logGroupName=group["logGroupName"], retentionInDays=7)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["package", "deploy", "status"])
    args = parser.parse_args()
    {"package": package, "deploy": deploy, "status": status}[args.command]()
