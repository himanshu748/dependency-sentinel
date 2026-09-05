"""Authenticated, stateless AgentCore advisory client."""

import json
import logging
import uuid

import boto3
from botocore.config import Config

logger = logging.getLogger(__name__)


class RuntimeClient:
    def __init__(self, arn: str, region: str, client=None):
        self.arn = arn
        self.client = client or boto3.client(
            "bedrock-agentcore",
            region_name=region,
            config=Config(read_timeout=180, retries={"total_max_attempts": 1}),
        )
        self.last_evidence = None

    def invoke(self, payload: dict) -> dict:
        session_id = str(uuid.uuid4())
        try:
            response = self.client.invoke_agent_runtime(
                agentRuntimeArn=self.arn,
                qualifier="DEFAULT",
                runtimeSessionId=session_id,
                contentType="application/json",
                payload=json.dumps(payload).encode(),
            )
            body = response["response"]
            try:
                result = json.loads(body.read())
            finally:
                body.close()
            if result.get("engine") != "strands-bedrock":
                raise ValueError("Runtime did not return verified Strands/Bedrock advice")
            self.last_evidence = {key: result[key] for key in ("engine", "tool_calls", "usage")}
            return result["advice"]
        finally:
            try:
                self.client.stop_runtime_session(
                    agentRuntimeArn=self.arn, runtimeSessionId=session_id, qualifier="DEFAULT"
                )
            except Exception:
                logger.warning("Session stop failed; the configured idle timeout remains active")
