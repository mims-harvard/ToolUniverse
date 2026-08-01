import sys
from types import SimpleNamespace

import pytest

from tooluniverse.llm_clients import OpenAICompatibleClient


class FakeRateLimitError(Exception):
    pass


class FakeCompletions:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs.get("stream"):
            return [
                SimpleNamespace(
                    choices=[SimpleNamespace(delta=SimpleNamespace(content="hel"))]
                ),
                SimpleNamespace(
                    choices=[SimpleNamespace(delta=SimpleNamespace(content="lo"))]
                ),
            ]
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))]
        )


class FakeOpenAIClient:
    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.completions = FakeCompletions()
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(
                create=self.completions.create,
                parse=self.completions.create,
            )
        )
        FakeOpenAIClient.instances.append(self)


@pytest.fixture(autouse=True)
def fake_openai(monkeypatch):
    FakeOpenAIClient.instances = []
    monkeypatch.setitem(
        sys.modules,
        "openai",
        SimpleNamespace(OpenAI=FakeOpenAIClient, RateLimitError=FakeRateLimitError),
    )
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)


def test_openai_compatible_client_uses_base_url(monkeypatch):
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.test/v1")

    client = OpenAICompatibleClient(
        "provider/model",
        logger=SimpleNamespace(warning=lambda *_: None, error=lambda *_: None),
    )

    assert FakeOpenAIClient.instances[0].kwargs == {
        "api_key": "test-key",
        "base_url": "https://example.test/v1",
        "max_retries": 0,
    }
    result = client.infer(
        messages=[{"role": "user", "content": "ping"}],
        temperature=0,
        max_tokens=16,
        return_json=True,
        max_retries=1,
        retry_delay=0,
    )
    assert result == "ok"
    assert FakeOpenAIClient.instances[0].completions.calls[0]["response_format"] == {
        "type": "json_object"
    }


def test_openai_compatible_default_max_tokens_from_env(monkeypatch):
    monkeypatch.setenv("OPENAI_MAX_TOKENS_BY_MODEL", '{"gpt-4o": 123}')
    client = OpenAICompatibleClient(
        "gpt-4o-mini",
        logger=SimpleNamespace(warning=lambda *_: None, error=lambda *_: None),
    )

    result = client.infer(
        messages=[{"role": "user", "content": "ping"}],
        temperature=None,
        max_tokens=None,
        return_json=False,
        max_retries=1,
        retry_delay=0,
    )

    assert result == "ok"
    assert FakeOpenAIClient.instances[0].completions.calls[0]["max_tokens"] == 123


def test_openai_reasoning_model_uses_completion_tokens(monkeypatch):
    monkeypatch.setenv("OPENAI_MAX_TOKENS_BY_MODEL", '{"o4-mini": 321}')
    client = OpenAICompatibleClient(
        "provider/o4-mini",
        logger=SimpleNamespace(warning=lambda *_: None, error=lambda *_: None),
    )

    result = client.infer(
        messages=[{"role": "user", "content": "ping"}],
        temperature=0.7,
        max_tokens=None,
        return_json=False,
        max_retries=1,
        retry_delay=0,
    )

    assert result == "ok"
    call = FakeOpenAIClient.instances[0].completions.calls[0]
    assert call["max_completion_tokens"] == 321
    assert "max_tokens" not in call
    assert "temperature" not in call


def test_openai_compatible_streaming():
    client = OpenAICompatibleClient(
        "provider/model",
        logger=SimpleNamespace(warning=lambda *_: None, error=lambda *_: None),
    )

    chunks = list(
        client.infer_stream(
            messages=[{"role": "user", "content": "ping"}],
            temperature=0,
            max_tokens=16,
            return_json=False,
            max_retries=1,
            retry_delay=0,
        )
    )

    assert chunks == ["hel", "lo"]
    call = FakeOpenAIClient.instances[0].completions.calls[0]
    assert call["stream"] is True
    assert call["max_tokens"] == 16


def test_openai_compatible_rate_limit_does_not_sleep_after_final_attempt(
    monkeypatch,
):
    client = OpenAICompatibleClient(
        "provider/model",
        logger=SimpleNamespace(warning=lambda *_: None, error=lambda *_: None),
    )
    completions = FakeOpenAIClient.instances[0].completions
    attempts = []

    def always_rate_limited(**kwargs):
        attempts.append(kwargs)
        raise FakeRateLimitError

    client.client.chat.completions.create = always_rate_limited
    sleeps = []
    monkeypatch.setattr("tooluniverse.llm_clients.time.sleep", sleeps.append)

    result = client.infer(
        messages=[{"role": "user", "content": "ping"}],
        temperature=0,
        max_tokens=16,
        return_json=False,
        max_retries=2,
        retry_delay=3,
    )

    assert result is None
    assert len(attempts) == 2
    assert sleeps == [3]
    assert completions.calls == []


def test_openai_compatible_non_retryable_error_is_not_reported_as_exhausted():
    errors = []
    client = OpenAICompatibleClient(
        "provider/model",
        logger=SimpleNamespace(warning=lambda *_: None, error=errors.append),
    )

    def fail_once(**kwargs):
        raise ValueError("invalid request")

    client.client.chat.completions.create = fail_once

    result = client.infer(
        messages=[{"role": "user", "content": "ping"}],
        temperature=0,
        max_tokens=16,
        return_json=False,
        max_retries=3,
        retry_delay=0,
    )

    assert result is None
    assert errors == ["OpenAI-compatible error: invalid request"]


def test_openai_compatible_retries_server_errors(monkeypatch):
    client = OpenAICompatibleClient(
        "provider/model",
        logger=SimpleNamespace(warning=lambda *_: None, error=lambda *_: None),
    )
    attempts = []

    class ServiceUnavailableError(Exception):
        status_code = 503

    def fail_then_succeed(**kwargs):
        attempts.append(kwargs)
        if len(attempts) == 1:
            raise ServiceUnavailableError
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))]
        )

    client.client.chat.completions.create = fail_then_succeed
    sleeps = []
    monkeypatch.setattr("tooluniverse.llm_clients.time.sleep", sleeps.append)

    result = client.infer(
        messages=[{"role": "user", "content": "ping"}],
        temperature=0,
        max_tokens=16,
        return_json=False,
        max_retries=2,
        retry_delay=3,
    )

    assert result == "ok"
    assert len(attempts) == 2
    assert sleeps == [3]


def test_openai_compatible_stream_retries_before_first_chunk(monkeypatch):
    client = OpenAICompatibleClient(
        "provider/model",
        logger=SimpleNamespace(warning=lambda *_: None, error=lambda *_: None),
    )
    attempts = []

    def create_stream(**kwargs):
        attempts.append(kwargs)
        if len(attempts) == 1:
            raise FakeRateLimitError
        return [
            SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content="ok"))]
            )
        ]

    client.client.chat.completions.create = create_stream
    sleeps = []
    monkeypatch.setattr("tooluniverse.llm_clients.time.sleep", sleeps.append)

    chunks = list(
        client.infer_stream(
            messages=[{"role": "user", "content": "ping"}],
            temperature=0,
            max_tokens=16,
            return_json=False,
            max_retries=2,
            retry_delay=3,
        )
    )

    assert chunks == ["ok"]
    assert len(attempts) == 2
    assert sleeps == [3]


def test_openai_compatible_custom_format_uses_parse_and_returns_dumped_model():
    client = OpenAICompatibleClient(
        "provider/model",
        logger=SimpleNamespace(warning=lambda *_: None, error=lambda *_: None),
    )
    calls = []
    response_format = object()

    def parse(**kwargs):
        calls.append(kwargs)
        parsed = SimpleNamespace(model_dump=lambda: {"answer": 42})
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(parsed=parsed))]
        )

    client.client.chat.completions.parse = parse

    result = client.infer(
        messages=[{"role": "user", "content": "Return a structured answer"}],
        temperature=0,
        max_tokens=16,
        return_json=False,
        custom_format=response_format,
        max_retries=1,
        retry_delay=0,
    )

    assert result == {"answer": 42}
    assert calls[0]["response_format"] is response_format


def test_openai_compatible_extracts_list_content_from_dict_chunk():
    chunk = {
        "choices": [
            {
                "delta": {
                    "content": [
                        {"text": "hel"},
                        {"text": "lo"},
                        {"type": "ignored"},
                    ]
                }
            }
        ]
    }

    assert OpenAICompatibleClient._extract_text_from_chunk(chunk) == "hello"
