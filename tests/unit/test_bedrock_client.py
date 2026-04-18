"""Unit tests for Bedrock Nova/Claude client helpers."""

from src.utils import bedrock_client as bc


def test_extract_nova_text_concat_blocks():
    body = {
        "output": {
            "message": {
                "role": "assistant",
                "content": [
                    {"text": '{"category": "Technical"}'},
                ],
            }
        },
        "usage": {"inputTokens": 10, "outputTokens": 5},
    }
    assert bc._extract_nova_text(body) == '{"category": "Technical"}'


def test_extract_nova_text_skips_non_text_blocks():
    body = {
        "output": {
            "message": {
                "content": [
                    {
                        "reasoningContent": {
                            "reasoningText": {"text": "[REDACTED]"}
                        }
                    },
                    {"text": "hello"},
                ]
            }
        }
    }
    assert bc._extract_nova_text(body) == "hello"


def test_infer_api_family_from_model_id(monkeypatch):
    monkeypatch.delenv("BEDROCK_API_FAMILY", raising=False)
    assert bc._infer_api_family("amazon.nova-micro-v1:0") == "nova"
    assert bc._infer_api_family("us.amazon.nova-lite-v1:0") == "nova"
    assert bc._infer_api_family("anthropic.claude-3-haiku-20240307-v1:0") == "claude"


def test_infer_api_family_env_override(monkeypatch):
    monkeypatch.setenv("BEDROCK_API_FAMILY", "claude")
    assert bc._infer_api_family("amazon.nova-micro-v1:0") == "claude"
