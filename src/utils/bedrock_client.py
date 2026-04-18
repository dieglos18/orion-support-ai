"""
Amazon Bedrock client wrapper with retry logic and error handling.

Supports Anthropic Claude (Messages API) and Amazon Nova (messages-v1 Invoke API).
"""
import json
import logging
import os
from typing import Any, Dict, List, Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

DEFAULT_MODEL_NOVA_MICRO = "amazon.nova-micro-v1:0"

# On-demand Standard tier (USD per 1K tokens) — verify against current AWS pricing
NOVA_MICRO_PRICE_INPUT_PER_1K = 0.000035
NOVA_MICRO_PRICE_OUTPUT_PER_1K = 0.00014

CLAUDE_HAIKU_PRICE_INPUT_PER_1K = 0.00025
CLAUDE_HAIKU_PRICE_OUTPUT_PER_1K = 0.00125

_READ_TIMEOUT = 120


def _resolve_bedrock_region() -> str:
    return (
        os.getenv("BEDROCK_REGION")
        or os.getenv("AWS_REGION")
        or os.getenv("AWS_DEFAULT_REGION")
        or "us-east-1"
    )


def _infer_api_family(model_id: str) -> str:
    override = os.getenv("BEDROCK_API_FAMILY", "").strip().lower()
    if override in ("nova", "claude"):
        return override
    mid = model_id.lower()
    if mid.startswith("anthropic."):
        return "claude"
    if "nova" in mid and (mid.startswith("amazon.") or mid.startswith("us.")):
        return "nova"
    return "claude"


class BedrockClient:
    """
    Wrapper for Amazon Bedrock invoke_model with retry logic and cost hints.

    Nova uses schemaVersion messages-v1; Claude uses the Anthropic Messages format.
    """

    def __init__(
        self,
        model_id: Optional[str] = None,
        region: Optional[str] = None,
        max_retries: int = 3,
    ):
        self.model_id = model_id or os.getenv(
            "BEDROCK_MODEL_ID", DEFAULT_MODEL_NOVA_MICRO
        )
        self._region = region or _resolve_bedrock_region()
        self._api_family = _infer_api_family(self.model_id)

        config = Config(
            region_name=self._region,
            retries={"max_attempts": max_retries, "mode": "adaptive"},
            read_timeout=_READ_TIMEOUT,
            connect_timeout=30,
        )

        self.client = boto3.client("bedrock-runtime", config=config)
        logger.info(
            "Initialized Bedrock client model=%s family=%s region=%s",
            self.model_id,
            self._api_family,
            self._region,
        )

    def invoke(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 2048,
        temperature: float = 0.3,
        enforce_json: bool = True,
    ) -> Dict[str, Any]:
        """
        Invoke the configured model. Returns a normalized shape for agents:

        content: str
        usage: {"input_tokens", "output_tokens"}
        stop_reason: optional str
        """
        try:
            if self._api_family == "nova":
                return self._invoke_nova(
                    system_prompt, user_message, max_tokens, temperature
                )
            return self._invoke_claude(
                system_prompt, user_message, max_tokens, temperature
            )
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_msg = e.response["Error"]["Message"]

            if error_code == "ThrottlingException":
                logger.error("Bedrock rate limit exceeded")
                raise
            if error_code == "ValidationException":
                logger.error("Invalid request: %s", error_msg)
                raise
            logger.error("Bedrock error: %s - %s", error_code, error_msg)
            raise

    def _invoke_claude(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int,
        temperature: float,
    ) -> Dict[str, Any]:
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_message},
            ],
        }

        logger.debug("Invoking Claude Bedrock (%s chars user)", len(user_message))

        response = self.client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(request_body),
            contentType="application/json",
            accept="application/json",
        )

        response_body = json.loads(response["body"].read())
        content_blocks = response_body.get("content", [])
        if not content_blocks:
            raise ValueError("Empty response from Bedrock (Claude)")

        content_text = content_blocks[0].get("text", "")
        usage_raw = response_body.get("usage", {})
        usage = {
            "input_tokens": usage_raw.get("input_tokens", 0),
            "output_tokens": usage_raw.get("output_tokens", 0),
        }
        logger.info(
            "Bedrock (Claude) tokens: %s in, %s out",
            usage["input_tokens"],
            usage["output_tokens"],
        )

        return {
            "content": content_text,
            "usage": usage,
            "stop_reason": response_body.get("stop_reason"),
        }

    def _invoke_nova(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int,
        temperature: float,
    ) -> Dict[str, Any]:
        request_body: Dict[str, Any] = {
            "schemaVersion": "messages-v1",
            "system": [{"text": system_prompt}],
            "messages": [
                {"role": "user", "content": [{"text": user_message}]},
            ],
            "inferenceConfig": {
                "maxTokens": max_tokens,
                "temperature": temperature,
            },
        }

        logger.debug("Invoking Nova Bedrock (%s chars user)", len(user_message))

        response = self.client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(request_body),
            contentType="application/json",
            accept="application/json",
        )

        response_body = json.loads(response["body"].read())
        content_text = _extract_nova_text(response_body)
        if not content_text:
            raise ValueError("Empty response from Bedrock (Nova)")

        usage_raw = response_body.get("usage", {})
        usage = {
            "input_tokens": usage_raw.get("inputTokens", usage_raw.get("input_tokens", 0)),
            "output_tokens": usage_raw.get(
                "outputTokens", usage_raw.get("output_tokens", 0)
            ),
        }
        logger.info(
            "Bedrock (Nova) tokens: %s in, %s out",
            usage["input_tokens"],
            usage["output_tokens"],
        )

        return {
            "content": content_text,
            "usage": usage,
            "stop_reason": response_body.get("stopReason")
            or response_body.get("stop_reason"),
        }

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate USD cost for the configured model family (on-demand list prices)."""
        if self._api_family == "nova":
            inp = NOVA_MICRO_PRICE_INPUT_PER_1K
            out = NOVA_MICRO_PRICE_OUTPUT_PER_1K
        else:
            inp = CLAUDE_HAIKU_PRICE_INPUT_PER_1K
            out = CLAUDE_HAIKU_PRICE_OUTPUT_PER_1K
        return (input_tokens / 1000) * inp + (output_tokens / 1000) * out


def _extract_nova_text(response_body: Dict[str, Any]) -> str:
    """Collect assistant text blocks from Nova InvokeModel response."""
    output = response_body.get("output") or {}
    message = output.get("message") or {}
    content: List[Any] = message.get("content") or []
    parts: List[str] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        text = block.get("text")
        if isinstance(text, str):
            parts.append(text)
    return "".join(parts)
