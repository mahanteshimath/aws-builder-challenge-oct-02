"""Amazon Bedrock Runtime (Converse API) client with timeouts and error classification."""
from __future__ import annotations

import os

DEFAULT_MODEL_ID = "us.amazon.nova-lite-v1:0"


class BedrockUnavailable(RuntimeError):
    def __init__(self, category: str):
        super().__init__(category)
        self.category = category


def bedrock_enabled() -> bool:
    return os.environ.get("ENABLE_BEDROCK", "false").lower() in ("1", "true", "yes")


def model_id() -> str:
    return os.environ.get("BEDROCK_MODEL_ID", DEFAULT_MODEL_ID)


def converse(system: str, user: str, max_tokens: int = 1500, client=None) -> str:
    """Return model text. Raises BedrockUnavailable(category) on any failure (no payload leakage)."""
    if not bedrock_enabled():
        raise BedrockUnavailable("disabled")
    try:
        if client is None:
            import boto3
            from botocore.config import Config
            client = boto3.client("bedrock-runtime", region_name=os.environ.get("AWS_REGION", "us-east-1"),
                                  config=Config(read_timeout=22, connect_timeout=3, retries={"max_attempts": 1}))
        resp = client.converse(modelId=model_id(), system=[{"text": system}],
                               messages=[{"role": "user", "content": [{"text": user}]}],
                               inferenceConfig={"maxTokens": max_tokens, "temperature": 0.2})
        parts = resp["output"]["message"]["content"]
        return "".join(p.get("text", "") for p in parts)
    except BedrockUnavailable:
        raise
    except Exception as exc:  # classify without leaking details
        name = type(exc).__name__
        code = getattr(exc, "response", {}).get("Error", {}).get("Code", "") if hasattr(exc, "response") else ""
        if code == "ThrottlingException" or "Throttl" in name:
            raise BedrockUnavailable("throttled") from exc
        if code in ("AccessDeniedException", "UnrecognizedClientException"):
            raise BedrockUnavailable("access_denied") from exc
        if code in ("ResourceNotFoundException", "ModelNotReadyException", "ValidationException"):
            raise BedrockUnavailable("model_unavailable") from exc
        if "Timeout" in name or "timed out" in str(exc).lower():
            raise BedrockUnavailable("timeout") from exc
        raise BedrockUnavailable("error") from exc
