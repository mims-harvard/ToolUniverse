from __future__ import annotations

import pytest

from examples.vsd.multiformat_contract_case_study import run_case

pytestmark = pytest.mark.unit


def test_multiformat_case_study_is_complete_and_deterministic():
    first = run_case()
    second = run_case()
    assert first == second
    assert first["case_count"] == 6
    assert first["operation_count"] == 10
    assert first["assertion_count"] == 27
    assert all(item["passed"] for item in first["assertions"])
