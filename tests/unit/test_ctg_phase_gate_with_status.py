"""search_clinical_trials dropped its phase>=2 gate whenever a status filter was set.

The tool documents "Limited to trials beyond phase 1" and implements it with a
hidden ``filter.advanced=(AREA[Phase]PHASE2 OR ... PHASE4)`` default. That
default was skipped whenever ``filter.overallStatus`` was present, guarded by a
comment about an ``AREA[HasResults]true`` clause that an earlier fix had already
deleted -- so the workaround outlived its reason and silently disabled the gate.

Confirmed live: adding the *narrowing* ``overall_status=["COMPLETED"]`` to a
metformin/lactic-acidosis search raised total_count from 2 to 3 and returned a
disjoint set of studies, and a RECRUITING pembrolizumab search returned 745
studies instead of 557 -- 188 of them phase 1 or early phase 1.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tooluniverse.ctg_tool import ClinicalTrialsSearchTool

_PHASE_GATE = "(AREA[Phase]PHASE2 OR AREA[Phase]PHASE3 OR AREA[Phase]PHASE4)"
_CONFIG = (
    Path(__file__).resolve().parents[2]
    / "src/tooluniverse/data/clinicaltrials_gov_tools.json"
)


@pytest.fixture
def tool():
    # Use the shipped config so the test tracks the real query_schema.
    configs = json.loads(_CONFIG.read_text())
    cfg = next(c for c in configs if c["name"] == "search_clinical_trials")
    return ClinicalTrialsSearchTool(cfg)


def _captured_params(tool, arguments):
    captured = {}

    def fake_query(endpoint_url, variables):
        captured.update(variables)
        return {"studies": [{"protocolSection": {}}], "totalCount": 1}

    with patch("tooluniverse.ctg_tool.execute_RESTful_query", side_effect=fake_query):
        with patch.object(tool, "_simplify_output", side_effect=lambda r: r):
            tool.run(dict(arguments))
    return captured


def test_phase_gate_applied_without_status_filter(tool):
    params = _captured_params(tool, {"condition": "diabetes"})

    assert params["filter.advanced"] == _PHASE_GATE


def test_phase_gate_still_applied_with_status_filter(tool):
    params = _captured_params(
        tool, {"condition": "diabetes", "overall_status": ["COMPLETED"]}
    )

    assert params["filter.advanced"] == _PHASE_GATE
    assert "COMPLETED" in str(params["filter.overallStatus"])


def test_phase_gate_applied_for_every_status_value(tool):
    for status in ("RECRUITING", "COMPLETED", "TERMINATED", "WITHDRAWN"):
        params = _captured_params(
            tool, {"condition": "diabetes", "overall_status": [status]}
        )
        assert params["filter.advanced"] == _PHASE_GATE, status


def test_status_alias_does_not_bypass_the_gate(tool):
    # `status` is mapped onto filter.overallStatus by the param-name mapper.
    params = _captured_params(tool, {"condition": "diabetes", "status": ["RECRUITING"]})

    assert params["filter.advanced"] == _PHASE_GATE


def test_status_filter_only_adds_a_constraint(tool):
    # Adding a status filter must narrow the query, never trade one filter for
    # another -- that swap is what let the result count grow from 2 to 3.
    without = _captured_params(tool, {"condition": "diabetes"})
    with_status = _captured_params(
        tool, {"condition": "diabetes", "overall_status": ["COMPLETED"]}
    )

    assert set(without) <= set(with_status)
    for key, value in without.items():
        assert with_status[key] == value, key
    assert "filter.overallStatus" in with_status
