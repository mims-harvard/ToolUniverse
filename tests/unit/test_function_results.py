"""What a caller receives from a scientist's own @remote_tool function.

Measured with `tu serve my_tool.py --share` and calls through the relay:
  - an embedding returned as a numpy array arrived as the string "[0. 3. 6. 9.]";
  - ValueError("sequence must be at least 10 residues") arrived as a retriable server error
    with "Retry the request" and "Check service status";
  - the server banner told the owner to `pip install --upgrade fastmcp` to 4.x, which
    ToolUniverse does not support.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np
import pytest

from tooluniverse.exceptions import ToolServerError, ToolValidationError
from tooluniverse.smcp import _json_default


def dumps(value):
    return json.loads(json.dumps(value, default=_json_default))


def test_a_numpy_array_is_numbers_not_text():
    assert dumps({"embedding": np.arange(4, dtype=np.float32) * 3}) == {
        "embedding": [0.0, 3.0, 6.0, 9.0]}


def test_numpy_scalars_are_numbers():
    assert dumps({"score": np.float64(0.25), "n": np.int64(3), "ok": np.bool_(True)}) == {
        "score": 0.25, "n": 3, "ok": True}


def test_a_dataframe_is_a_list_of_rows():
    pd = pytest.importorskip("pandas")
    frame = pd.DataFrame({"gene": ["TP53", "BRCA1"], "score": [0.9, 0.4]})

    assert dumps({"hits": frame}) == {"hits": [
        {"gene": "TP53", "score": 0.9}, {"gene": "BRCA1", "score": 0.4}]}


def test_a_series_is_a_list():
    pd = pytest.importorskip("pandas")

    assert dumps({"s": pd.Series([1, 2])}) == {"s": [1, 2]}


def test_anything_else_keeps_the_old_fallback():
    class Thing:
        def __str__(self):
            return "thing"

    assert dumps({"x": Thing()}) == {"x": "thing"}


def classify(exception):
    from tooluniverse.execute_function import ToolUniverse

    # A @remote_tool function's wrapper is a plain class without handle_error.
    universe = SimpleNamespace(_get_tool_instance=lambda name, cache=True: object())
    return ToolUniverse._classify_exception(universe, exception, "strict", {})


def test_a_functions_own_value_error_is_an_input_problem():
    error = classify(ValueError("sequence must be at least 10 residues"))

    assert isinstance(error, ToolValidationError)
    assert error.retriable is False
    assert "sequence must be at least 10 residues" in str(error)


def test_other_failures_stay_server_errors():
    assert isinstance(classify(RuntimeError("CUDA out of memory")), ToolServerError)


def test_the_upgrade_notice_is_off():
    import fastmcp

    import tooluniverse.smcp

    assert fastmcp.settings.check_for_updates == "off"


# ── through the server `tu serve my_tool.py` builds ──────────────────────────────


@pytest.fixture
def served(tmp_path, monkeypatch):
    """Build the server as mcp_tool_registry._start_server_for_port does, without starting it."""
    import asyncio

    from tooluniverse import mcp_tool_registry as registry
    from tooluniverse.execute_function import ToolUniverse
    from tooluniverse.smcp import SMCP

    monkeypatch.setenv("TOOLUNIVERSE_CACHE_DIR", str(tmp_path / "cache"))
    saved = dict(registry._mcp_tool_registry)
    registry._mcp_tool_registry.clear()

    @registry.remote_tool
    def embed(sequence: str) -> dict:
        """Embed one sequence."""
        return {"embedding": np.arange(3, dtype=np.float32) * len(sequence)}

    @registry.remote_tool
    def strict(sequence: str) -> dict:
        """Refuse short sequences."""
        raise ValueError("sequence must be at least 10 residues")

    tu = ToolUniverse(tool_files={}, keep_default_tools=False, load_workspace=False)
    for info in registry._mcp_tool_registry.values():
        tu.register_custom_tool(
            tool_class=info["class"], tool_name=info["type"], instantiate=True,
            tool_config={"name": info["name"], "type": info["type"],
                         "description": info["description"],
                         "parameter": info["parameter_schema"], "category": "mcp_tools"})
    server = SMCP(name="probe", tooluniverse_config=tu, auto_expose_tools=True,
                  search_enabled=False, max_workers=1, persist_oversized_results=False,
                  strict_input_schemas=True)

    def call(name, arguments):
        tool = asyncio.run(server.get_tool(name))
        result = asyncio.run(tool.run(arguments))
        return json.loads(result.content[0].text)

    yield call
    registry._mcp_tool_registry.clear()
    registry._mcp_tool_registry.update(saved)


def test_a_served_function_returns_its_array_as_numbers(served):
    assert served("embed", {"sequence": "MKV"}) == {"embedding": [0.0, 3.0, 6.0]}


def test_a_served_functions_refusal_is_not_retriable(served):
    body = served("strict", {"sequence": "MKV"})

    assert body["error_details"]["type"] == "ToolValidationError"
    assert body["error_details"]["retriable"] is False
