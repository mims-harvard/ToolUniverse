import sys
from types import SimpleNamespace

import pytest

from tooluniverse.llm_clients import BedrockClient


class FakeBedrockRuntime:
    def __init__(self):
        self.calls = []
        self.stream_calls = []

    def converse(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "output": {
                "message": {
                    "content": [
                        {"text": "hello"},
                        {"text": " world"},
                    ]
                }
            }
        }

    def converse_stream(self, **kwargs):
        self.stream_calls.append(kwargs)
        return {
            "stream": [
                {"contentBlockDelta": {"delta": {"text": "hel"}}},
                {"contentBlockDelta": {"delta": {"text": "lo"}}},
            ]
        }


@pytest.fixture
def fake_runtime(monkeypatch):
    runtime = FakeBedrockRuntime()

    class FakeSession:
        region_name = "us-west-2"

        def client(self, service_name, region_name=None):
            assert service_name == "bedrock-runtime"
            assert region_name == "us-east-1"
            return runtime

    monkeypatch.setitem(sys.modules, "boto3", SimpleNamespace(Session=FakeSession))
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    return runtime


def test_bedrock_client_uses_converse_api(fake_runtime):
    logger = SimpleNamespace(warning=lambda *_: None, error=lambda *_: None)
    client = BedrockClient("anthropic.claude-3-5-sonnet-20240620-v1:0", logger=logger)

    result = client.infer(
        messages=[
            {"role": "system", "content": "You are concise."},
            {"role": "user", "content": "Say hello"},
        ],
        temperature=0,
        max_tokens=32,
        return_json=True,
        max_retries=1,
        retry_delay=0,
    )

    assert result == "hello world"
    call = fake_runtime.calls[0]
    assert call["modelId"] == "anthropic.claude-3-5-sonnet-20240620-v1:0"
    assert call["messages"] == [{"role": "user", "content": [{"text": "Say hello"}]}]
    assert call["system"] == [
        {"text": "You are concise."},
        {"text": "Return only valid JSON."},
    ]
    assert call["inferenceConfig"] == {"temperature": 0, "maxTokens": 32}


def test_bedrock_streaming_uses_converse_stream(fake_runtime):
    logger = SimpleNamespace(warning=lambda *_: None, error=lambda *_: None)
    client = BedrockClient("amazon.nova-pro-v1:0", logger=logger)

    chunks = list(
        client.infer_stream(
            messages=[{"role": "user", "content": "Say hello"}],
            temperature=None,
            max_tokens=8,
            return_json=False,
            max_retries=1,
            retry_delay=0,
        )
    )

    assert chunks == ["hel", "lo"]
    assert fake_runtime.stream_calls[0]["inferenceConfig"] == {"maxTokens": 8}


def test_bedrock_client_uses_profile_region(monkeypatch):
    runtime = FakeBedrockRuntime()
    observed = {}

    class FakeSession:
        region_name = "us-west-2"

        def client(self, service_name, region_name=None):
            observed["service_name"] = service_name
            observed["region_name"] = region_name
            return runtime

    monkeypatch.setitem(sys.modules, "boto3", SimpleNamespace(Session=FakeSession))
    for name in ("BEDROCK_REGION", "AWS_REGION", "AWS_DEFAULT_REGION"):
        monkeypatch.delenv(name, raising=False)

    logger = SimpleNamespace(warning=lambda *_: None, error=lambda *_: None)
    BedrockClient("amazon.nova-lite-v1:0", logger=logger)

    assert observed == {
        "service_name": "bedrock-runtime",
        "region_name": "us-west-2",
    }
