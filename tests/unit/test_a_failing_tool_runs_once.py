"""A tool that raises must be executed once, not twice.

`_execute_tool_with_stream` and its async twin used to put the real
`tool_instance.run(...)` call inside the same `try` as `inspect.signature`,
under `except (ValueError, TypeError)`. That handler was written for a callable
with no introspectable signature, but it could not tell that apart from the
tool's own body raising -- so a tool whose `run()` raised either exception was
executed a **second** time, with `use_cache`, `validate` and `stream_callback`
dropped for the retry (#905).

`ValueError` is not an exotic case: `json.JSONDecodeError` and
`requests.exceptions.JSONDecodeError` both subclass it, so any REST wrapper
that let a response parse error escape sent its request twice. A shipped tool
reached it as well -- `MCPAutoLoaderTool` raises `ValueError` for
`operation="call_tool"` with no `tool_name`, and was observed running twice.

These tests pin both halves: a raising tool runs once, and the parameters the
retry used to drop are still forwarded to the tools that declare them. Putting
the call back inside the handler makes the counting tests report 2.
"""

import asyncio
import inspect

import pytest

from tooluniverse import ToolUniverse
from tooluniverse.base_tool import BaseTool


class _Counting(BaseTool):
    """Base for tools that count their own invocations."""

    def __init__(self, config=None):
        super().__init__(config or {"name": "counting"})
        self.calls = 0
        self.seen_kwargs = []


class _RaisesValueError(_Counting):
    def run(self, arguments=None, use_cache=False, validate=True):
        self.calls += 1
        raise ValueError("Expecting value: line 1 column 1 (char 0)")


class _RaisesTypeError(_Counting):
    def run(self, arguments=None, use_cache=False, validate=True):
        self.calls += 1
        raise TypeError("unsupported operand type(s) for +: 'int' and 'str'")


class _RaisesRuntimeError(_Counting):
    def run(self, arguments=None, use_cache=False, validate=True):
        self.calls += 1
        raise RuntimeError("an exception the old handler never caught")


class _AcceptsEverything(_Counting):
    def run(self, arguments=None, use_cache=False, validate=True, stream_callback=None):
        self.calls += 1
        self.seen_kwargs.append(
            {
                "use_cache": use_cache,
                "validate": validate,
                "stream_callback": stream_callback,
            }
        )
        return {"ok": True}


class _AcceptsOnlyArguments(_Counting):
    def run(self, arguments=None):
        self.calls += 1
        self.seen_kwargs.append({})
        return {"ok": "minimal"}


class _UninspectableSignature(_Counting):
    """`inspect.signature(instance.run)` raises for this one.

    That is the case the old handler genuinely existed for, and it must keep
    working: the tool is still called, once, with arguments alone.
    """

    def run(self, arguments=None):
        self.calls += 1
        return {"ok": "uninspectable"}

    run.__signature__ = "not a signature at all"


def _register(tu, name, instance):
    config = {
        "name": name,
        "type": type(instance).__name__,
        "description": "a tool used by this test",
        "cacheable": False,
        "parameter": {"type": "object", "properties": {"q": {"type": "string"}}},
    }
    tu.callable_functions[name] = instance
    tu.all_tool_dict[name] = config
    return config


@pytest.mark.parametrize(
    ("tool_class", "raised"),
    [
        (_RaisesValueError, ValueError),
        (_RaisesTypeError, TypeError),
        (_RaisesRuntimeError, RuntimeError),
    ],
    ids=["ValueError", "TypeError", "RuntimeError"],
)
def test_a_tool_that_raises_is_executed_exactly_once(tool_class, raised):
    """One call, whatever the tool raises.

    RuntimeError is the control. The old handler never caught it, so that case
    was always executed once and passes before and after the fix. It is here so
    that a weakened assertion cannot make the other two look fixed: if "once"
    were trivially true, the control would be the only passing case.
    """
    tu = ToolUniverse()
    instance = tool_class()
    _register(tu, "raiser", instance)

    result = tu.run_one_function({"name": "raiser", "arguments": {"q": "x"}})

    assert instance.calls == 1, (
        f"run() was called {instance.calls} times for a tool raising "
        f"{raised.__name__}. The tool's own exception must not be mistaken for "
        "a signature-inspection failure and retried."
    )
    assert isinstance(result, dict) and result.get("status") == "error", (
        f"Expected the raised {raised.__name__} to be classified into an error "
        f"result, got {result!r}"
    )


def test_the_parameters_the_retry_used_to_drop_are_still_forwarded():
    """Narrowing the handler must not stop forwarding the optional parameters.

    The retry called `run(arguments)` and nothing else, which is how
    `use_cache` and `validate` went missing on the second attempt. A "fix" that
    simply stopped passing them would satisfy the counting tests above, so this
    is the other half of the contract.
    """
    tu = ToolUniverse()
    instance = _AcceptsEverything()
    _register(tu, "accepts", instance)

    received = []

    def callback(chunk):
        received.append(chunk)

    result, _ = tu._execute_tool_with_stream(
        instance,
        {"q": "x"},
        stream_callback=callback,
        use_cache=True,
        validate=False,
    )

    assert result == {"ok": True}
    assert instance.calls == 1
    seen = instance.seen_kwargs[0]
    assert seen["use_cache"] is True
    assert seen["validate"] is False
    assert seen["stream_callback"] is callback


def test_a_tool_that_declares_only_arguments_is_called_with_only_arguments():
    tu = ToolUniverse()
    instance = _AcceptsOnlyArguments()
    _register(tu, "minimal", instance)

    result, _ = tu._execute_tool_with_stream(
        instance, {"q": "x"}, stream_callback=None, use_cache=True, validate=True
    )

    assert result == {"ok": "minimal"}
    assert instance.calls == 1


def test_a_run_with_no_introspectable_signature_is_still_called_once():
    tu = ToolUniverse()
    instance = _UninspectableSignature()
    _register(tu, "uninspectable", instance)

    with pytest.raises((ValueError, TypeError)):
        inspect.signature(instance.run)

    result, _ = tu._execute_tool_with_stream(
        instance, {"q": "x"}, stream_callback=None, use_cache=True, validate=True
    )

    assert result == {"ok": "uninspectable"}
    assert instance.calls == 1


def test_deciding_which_parameters_a_tool_accepts_does_not_execute_it():
    tu = ToolUniverse()
    instance = _AcceptsEverything()

    kwargs = tu._supported_run_kwargs(
        instance, stream_callback=None, use_cache=True, validate=False
    )

    assert instance.calls == 0
    assert kwargs == {"use_cache": True, "validate": False}, (
        "stream_callback is None here, so it should not be offered; the two "
        f"declared flags should be. Got {kwargs!r}"
    )


@pytest.mark.parametrize(
    ("tool_class", "raised"),
    [(_RaisesValueError, ValueError), (_RaisesTypeError, TypeError)],
    ids=["ValueError", "TypeError"],
)
def test_the_async_path_also_runs_a_failing_tool_once(tool_class, raised):
    tu = ToolUniverse()
    instance = tool_class()
    _register(tu, "async_raiser", instance)

    async def call():
        return await tu._execute_tool_with_stream_async(
            instance, {"q": "x"}, stream_callback=None, use_cache=True, validate=True
        )

    with pytest.raises(raised):
        asyncio.run(call())

    assert instance.calls == 1, (
        f"The async twin called run() {instance.calls} times for a tool "
        f"raising {raised.__name__}; it carried the same retry."
    )
