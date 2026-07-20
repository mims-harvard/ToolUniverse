"""Regression guard: MultiAgentLiteratureSearch's `max_iterations` and
`quality_threshold` were wrongly marked `required` in
literature_search_tools.json even though each has a `default` -- but unlike
every other tool in the round-37 backlog, these two aren't just "correctly
defaulted in Python", they're never read at all by
compose_scripts/enhanced_multi_agent_literature_search.py's compose()
(confirmed by grepping the whole 314-line file). The search always runs a
single pass (the overall-summary agent call hardcodes "iterations": "1"),
and QualityCheckerAgent is listed as a required dependency but never
invoked by the actual search flow. Fixed by removing both from `required`
and correcting the tool's own description (and each param's description)
to stop promising iterative/quality-threshold behavior that isn't wired up
yet.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tooluniverse.compose_scripts.enhanced_multi_agent_literature_search import (
    compose,
)

pytestmark = pytest.mark.unit

_DATA_DIR = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data"


def _tool_config():
    configs = json.loads((_DATA_DIR / "literature_search_tools.json").read_text())
    for cfg in configs:
        if cfg["name"] == "MultiAgentLiteratureSearch":
            return cfg
    raise AssertionError("MultiAgentLiteratureSearch not found")


def test_requires_only_query():
    cfg = _tool_config()
    assert cfg["parameter"]["required"] == ["query"]


def test_description_no_longer_promises_iterative_quality_check():
    cfg = _tool_config()
    assert "iteratively" not in cfg["description"]
    assert "not currently applied" in cfg["parameter"]["properties"]["max_iterations"]["description"].lower()
    assert "not currently applied" in cfg["parameter"]["properties"]["quality_threshold"]["description"].lower()


def test_max_iterations_and_quality_threshold_never_read_by_compose():
    """Static guard: if a future change wires these params into real
    behavior, this test should be updated (and the schema/description
    honesty fix above should be revisited) rather than silently going
    stale."""
    import inspect
    import tooluniverse.compose_scripts.enhanced_multi_agent_literature_search as mod

    source = inspect.getsource(mod)
    assert '"max_iterations"' not in source
    assert "'max_iterations'" not in source
    assert '"quality_threshold"' not in source
    assert "'quality_threshold'" not in source


def test_compose_completes_with_max_iterations_and_quality_threshold_omitted():
    """End-to-end: the search flow completes identically whether or not
    max_iterations/quality_threshold are present in arguments, since
    they're never read."""
    memory_manager = MagicMock()
    memory_manager.create_session.return_value = "session-123"
    memory_manager.get_context_for_agent.return_value = {}

    def fake_call_tool(name, args):
        if name == "IntentAnalyzerAgent":
            return {"user_intent": "test intent", "search_plans": []}
        if name == "OverallSummaryAgent":
            return {"summary": "done"}
        raise AssertionError(f"unexpected call_tool: {name}")

    emit_event = MagicMock()
    stream_callback = MagicMock()

    result = compose(
        {"query": "CRISPR gene editing"},
        tooluniverse=MagicMock(),
        call_tool=fake_call_tool,
        stream_callback=stream_callback,
        emit_event=emit_event,
        memory_manager=memory_manager,
    )

    assert result["success"] is True
    assert result["results"]["total_papers"] == 0
