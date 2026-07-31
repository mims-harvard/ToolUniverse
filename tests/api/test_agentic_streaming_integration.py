import asyncio
import json
import sys
import types

import pytest


# Stub network-heavy dependency loaded by tooluniverse.__init__
if "rcsbapi" not in sys.modules:
    rcsbapi_module = types.ModuleType("rcsbapi")
    rcsbapi_data_module = types.ModuleType("rcsbapi.data")

    class _DummyDataQuery:
        def __init__(self, *args, **kwargs):
            pass

        def exec(self):  # pragma: no cover
            return {}

    rcsbapi_data_module.DataQuery = _DummyDataQuery
    rcsbapi_module.data = rcsbapi_data_module
    sys.modules["rcsbapi"] = rcsbapi_module
    sys.modules["rcsbapi.data"] = rcsbapi_data_module


from tooluniverse.agentic_tool import AgenticTool
from tooluniverse.execute_function import ToolUniverse
from tooluniverse.smcp import SMCP


class _StreamingLLMClient:
    def __init__(self, chunks):
        self.chunks = chunks
        self.stream_called = False
        self.infer_called = False

    def infer_stream(
        self,
        messages,
        temperature,
        max_tokens,
        return_json,
        custom_format=None,
        max_retries=5,
        retry_delay=5,
    ):
        self.stream_called = True
        for chunk in self.chunks:
            yield chunk

    def infer(
        self,
        messages,
        temperature,
        max_tokens,
        return_json,
        custom_format=None,
        max_retries=5,
        retry_delay=5,
    ):
        self.infer_called = True
        return "".join(self.chunks)


class _FailingStreamingLLMClient(_StreamingLLMClient):
    def infer_stream(
        self,
        messages,
        temperature,
        max_tokens,
        return_json,
        custom_format=None,
        max_retries=5,
        retry_delay=5,
    ):
        self.stream_called = True
        raise RuntimeError("stream broken")


@pytest.mark.integration
class TestAgenticTool(AgenticTool):
    client_factory = None

    def __init__(self, tool_config):
        if TestAgenticTool.client_factory is None:
            raise RuntimeError("client_factory must be set before instantiation")
        self._test_client = TestAgenticTool.client_factory()
        super().__init__(tool_config)

    def _try_initialize_api(self):
        self._llm_client = self._test_client
        self._is_available = True
        self._initialization_error = None
        self._current_api_type = "TEST"
        self._current_model_id = "stub-model"


def _agentic_config(name="TestAgenticTool"):
    return {
        "name": name,
        "type": name,
        "description": "streaming test tool",
        "prompt": "Answer succinctly: {question}",
        "input_arguments": ["question"],
        "parameter": {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "response_format": {"type": "string"},
            },
            "required": ["question"],
        },
        "configs": {
            "api_type": "CHATGPT",
            "model_id": "stub-model",
            "return_metadata": False,
            "validate_api_key": False,
        },
    }


def _register_agentic_tool(tool_universe, tool_cls, config, client):
    tool_cls.client_factory = lambda: client
    instance = tool_cls(config)
    tool_universe.register_custom_tool(tool_cls, tool_name=config["name"], tool_config=config)
    tool_universe.callable_functions[config["name"]] = instance
    tool_cls.client_factory = None
    return instance


def test_agentic_tool_streaming_uses_callback():
    tu = ToolUniverse(tool_files={}, keep_default_tools=False)
    client = _StreamingLLMClient(["chunk-1", "chunk-2"])
    config = _agentic_config("AgenticStreamingTool")
    tool = _register_agentic_tool(tu, TestAgenticTool, config, client)

    captured = []
    result = tool.run({"question": "hello"}, stream_callback=captured.append)

    assert result == "chunk-1chunk-2"
    assert captured == ["chunk-1", "chunk-2"]
    assert client.stream_called is True
    assert client.infer_called is False


def test_agentic_tool_streaming_falls_back_to_buffered_result():
    tu = ToolUniverse(tool_files={}, keep_default_tools=False)
    client = _FailingStreamingLLMClient(["fallback"])
    config = _agentic_config("AgenticStreamingFallbackTool")
    tool = _register_agentic_tool(tu, TestAgenticTool, config, client)

    captured = []
    result = tool.run({"question": "hi"}, stream_callback=captured.append)

    assert result == "fallback"
    assert captured == ["fallback"]
    assert client.stream_called is True
    assert client.infer_called is True


class _DummyCtx:
    def __init__(self):
        self.messages = []

    async def info(self, message, logger_name=None, extra=None):
        self.messages.append(message)


@pytest.mark.asyncio
async def test_smcp_tool_emits_stream_logs():
    tu = ToolUniverse(tool_files={}, keep_default_tools=False)
    client = _StreamingLLMClient(["log-1", "log-2"])
    config = _agentic_config("AgenticSMCPStreamTool")
    _register_agentic_tool(tu, TestAgenticTool, config, client)

    smcp = SMCP(
        tooluniverse_config=tu,
        auto_expose_tools=False,
        search_enabled=False,
        hooks_enabled=False,
    )

    tool_config = tu.all_tool_dict[config["name"]]
    smcp._create_mcp_tool_from_tooluniverse(tool_config)

    mcp_tool = await smcp.get_tool(config["name"])
    dynamic_fn = mcp_tool.fn

    ctx = _DummyCtx()
    result = await dynamic_fn(
        question="How are you?",
        _tooluniverse_stream=True,
        ctx=ctx,
    )

    # Allow thread-safe callbacks to finish
    await asyncio.sleep(0)

    assert json.loads(result) == {"result": "log-1log-2"}
    assert ctx.messages == ["log-1", "log-2"]
