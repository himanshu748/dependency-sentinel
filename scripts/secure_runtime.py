"""Opt-in KMS log encryption, retention and management-event audit for AgentCore."""

import argparse
import json
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

ROOT = Path(__file__).resolve().parents[1]


def secure_runtime(*, allow_paid=False, audit=False):
    if not allow_paid:
        raise SystemExit("KMS and audit storage may incur charges; use --allow-paid")
    state = json.loads((ROOT / ".agentcore/deployment.json").read_text())
    region = state["region"]
    session = boto3.Session(region_name=region)
    account = session.client("sts").get_caller_identity()["Account"]
    if not state["arn"].startswith(f"arn:aws:bedrock-agentcore:{region}:{account}:"):
        raise SystemExit("Deployment state does not match this AWS account")
    logs = session.client("logs")
    groups = logs.describe_log_groups(
        logGroupNamePrefix=f"/aws/bedrock-agentcore/runtimes/{state['id']}-"
    )["logGroups"]
    if not groups:
        raise SystemExit("No runtime log group yet; inspect runtime status")
    kms = session.client("kms")
    alias = "alias/afh-" + ROOT.name + "-runtime-logs"
    try:
        key = kms.describe_key(KeyId=alias)["KeyMetadata"]
    except kms.exceptions.NotFoundException:
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "AccountAdministration",
                    "Effect": "Allow",
                    "Principal": {"AWS": f"arn:aws:iam::{account}:root"},
                    "Action": "kms:*",
                    "Resource": "*",
                },
                {
                    "Sid": "ScopedCloudWatchEncryption",
                    "Effect": "Allow",
                    "Principal": {"Service": f"logs.{region}.amazonaws.com"},
                    "Action": [
                        "kms:Encrypt",
                        "kms:Decrypt",
                        "kms:ReEncrypt*",
                        "kms:GenerateDataKey*",
                        "kms:DescribeKey",
                    ],
                    "Resource": "*",
                    "Condition": {
                        "ArnEquals": {
                            "kms:EncryptionContext:aws:logs:arn": [
                                f"arn:aws:logs:{region}:{account}:log-group:{g['logGroupName']}"
                                for g in groups
                            ]
                        }
                    },
                },
            ],
        }
        key = kms.create_key(
            Description=ROOT.name + " AgentCore log encryption",
            Policy=json.dumps(policy),
            Tags=[{"TagKey": "Project", "TagValue": ROOT.name}],
        )["KeyMetadata"]
        kms.create_alias(AliasName=alias, TargetKeyId=key["KeyId"])
    if key["KeyState"] != "Enabled":
        raise SystemExit("Runtime log encryption key is not enabled")
    kms.enable_key_rotation(KeyId=key["KeyId"])
    for group in groups:
        logs.associate_kms_key(logGroupName=group["logGroupName"], kmsKeyId=key["Arn"])
        logs.put_retention_policy(logGroupName=group["logGroupName"], retentionInDays=7)
    if audit:
        # A single private management-event trail for this hackathon. No data events.
        trail_name = "AgentsForHumansManagement"
        trail_arn = f"arn:aws:cloudtrail:{region}:{account}:trail/{trail_name}"
        bucket = state["bucket"]
        s3 = session.client("s3")
        try:
            policy = json.loads(s3.get_bucket_policy(Bucket=bucket)["Policy"])
        except ClientError as error:
            if error.response["Error"]["Code"] != "NoSuchBucketPolicy":
                raise
            policy = {"Version": "2012-10-17", "Statement": []}
        statements = [
            {
                "Sid": "AFHTrailAclCheck",
                "Effect": "Allow",
                "Principal": {"Service": "cloudtrail.amazonaws.com"},
                "Action": "s3:GetBucketAcl",
                "Resource": f"arn:aws:s3:::{bucket}",
                "Condition": {"StringEquals": {"aws:SourceArn": trail_arn}},
            },
            {
                "Sid": "AFHTrailDelivery",
                "Effect": "Allow",
                "Principal": {"Service": "cloudtrail.amazonaws.com"},
                "Action": "s3:PutObject",
                "Resource": f"arn:aws:s3:::{bucket}/audit/AWSLogs/{account}/*",
                "Condition": {
                    "StringEquals": {
                        "aws:SourceArn": trail_arn,
                        "s3:x-amz-acl": "bucket-owner-full-control",
                    }
                },
            },
        ]
        known = {s.get("Sid") for s in policy["Statement"]}
        policy["Statement"].extend(s for s in statements if s["Sid"] not in known)
        s3.put_bucket_policy(Bucket=bucket, Policy=json.dumps(policy))
        cloudtrail = session.client("cloudtrail")
        trails = cloudtrail.describe_trails(trailNameList=[trail_name])["trailList"]
        if not trails:
            cloudtrail.create_trail(
                Name=trail_name,
                S3BucketName=bucket,
                S3KeyPrefix="audit",
                IncludeGlobalServiceEvents=True,
                IsMultiRegionTrail=False,
                EnableLogFileValidation=True,
                TagsList=[{"Key": "Event", "Value": "AgentsForHumans"}],
            )
        cloudtrail.put_event_selectors(
            TrailName=trail_name,
            EventSelectors=[
                {"ReadWriteType": "All", "IncludeManagementEvents": True, "DataResources": []}
            ],
        )
        cloudtrail.start_logging(Name=trail_name)
        print(
            json.dumps({"audit_logging": cloudtrail.get_trail_status(Name=trail_name)["IsLogging"]})
        )
    verified = logs.describe_log_groups(
        logGroupNamePrefix=f"/aws/bedrock-agentcore/runtimes/{state['id']}-"
    )["logGroups"]
    assert all(g.get("kmsKeyId") == key["Arn"] and g.get("retentionInDays") == 7 for g in verified)
    print(
        json.dumps({"runtime": state["id"], "kms_encryption_configured": True, "retention_days": 7})
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-paid", action="store_true")
    parser.add_argument(
        "--audit", action="store_true", help="Configure the shared management-event trail"
    )
    args = parser.parse_args()
    secure_runtime(allow_paid=args.allow_paid, audit=args.audit)
