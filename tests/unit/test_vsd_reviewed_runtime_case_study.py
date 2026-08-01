from __future__ import annotations

import pytest

from examples.vsd.reviewed_runtime_case_study import run_case

pytestmark = pytest.mark.unit


def test_reviewed_runtime_portfolio_is_complete_and_deterministic():
    first = run_case()
    second = run_case()
    assert first == second
    assert first["runtime_case_count"] == 10
    assert first["assertion_count"] == 33
    assert first["promotion"]["loaded_tools"] == ["PromotedSMNPanelSOAP"]
    assert all(item["passed"] for item in first["assertions"])
