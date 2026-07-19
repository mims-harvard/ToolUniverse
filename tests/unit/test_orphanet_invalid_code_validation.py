"""Regression guard for Fix-R20D-1: 5 of 7 code-based OrphanetTool operations
silently returned status:"success" with empty payloads for a nonexistent
ORPHA code, instead of erroring like their siblings Orphanet_get_disease and
Orphanet_get_phenotypes already correctly do.

Confirmed live for ORPHA:999999999 (a nonexistent code): the affected
operations (get_genes, get_epidemiology, get_natural_history,
get_classification, get_icd_mapping) hit a data-specific Orphadata/RDcode
endpoint that 404s both when the disease code itself doesn't exist AND when
a real disease legitimately has no records of that data type -- the old
code couldn't tell those two cases apart and always returned empty success.
Fixed by adding an explicit existence check (the RDcode Name endpoint 404s
only when the orpha_code itself is invalid) before the data fetch, reusing
that endpoint from _get_genes' existing disease_name lookup for that tool
and via a shared _orpha_code_exists() helper for the other four.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.orphanet_tool import OrphanetTool

pytestmark = pytest.mark.unit


def _tool():
    return OrphanetTool({"name": "orphanet_test"})


def _resp(status_code, json_body=None):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_body or {}
    if status_code >= 400:
        import requests

        http_err = requests.exceptions.HTTPError(response=r)
        r.raise_for_status = MagicMock(side_effect=http_err)
    else:
        r.raise_for_status = MagicMock()
    return r


@pytest.mark.parametrize(
    "operation",
    [
        "get_genes",
        "get_epidemiology",
        "get_natural_history",
        "get_classification",
        "get_icd_mapping",
    ],
)
def test_invalid_orpha_code_returns_error_not_silent_success(operation):
    tool = _tool()

    def fake_get(url, **kwargs):
        # Every endpoint 404s for this nonexistent code, including the
        # RDcode Name existence-check endpoint.
        return _resp(404)

    with patch("tooluniverse.orphanet_tool.requests.get", side_effect=fake_get):
        result = tool.run({"operation": operation, "orpha_code": "999999999"})

    assert result["status"] == "error"
    assert "not found" in result["error"].lower()
    assert "999999999" in result["error"]


@pytest.mark.parametrize(
    "operation,data_url_fragment",
    [
        ("get_genes", "rd-associated-genes/orphacodes/586"),
        ("get_epidemiology", "rd-epidemiology/orphacodes/586"),
        ("get_natural_history", "rd-natural_history/orphacodes/586"),
        ("get_classification", "Classification"),
        ("get_icd_mapping", "ICD10"),
    ],
)
def test_valid_code_with_no_data_still_returns_success_empty(
    operation, data_url_fragment
):
    """A real disease code that exists (Name endpoint returns 200) but
    happens to have no records for this specific data type must still
    return status:success with an empty payload -- not an error. This is
    the pre-existing, correct behavior for genuinely-empty-but-valid
    diseases and must not regress."""
    tool = _tool()

    def fake_get(url, **kwargs):
        if url.endswith("/orphacode/586/Name"):
            return _resp(200, {"Preferred term": "Test Disease"})
        # The actual data endpoint has nothing for this disease.
        return _resp(404)

    with patch("tooluniverse.orphanet_tool.requests.get", side_effect=fake_get):
        result = tool.run({"operation": operation, "orpha_code": "586"})

    assert result["status"] == "success"


def test_get_disease_and_get_phenotypes_unaffected_by_new_helper():
    """Sibling operations that already had correct not-found handling
    before this fix keep working identically."""
    tool = _tool()

    def fake_get(url, **kwargs):
        return _resp(404)

    with patch("tooluniverse.orphanet_tool.requests.get", side_effect=fake_get):
        disease_result = tool.run(
            {"operation": "get_disease", "orpha_code": "999999999"}
        )
        phenotype_result = tool.run(
            {"operation": "get_phenotypes", "orpha_code": "999999999"}
        )

    assert disease_result["status"] == "error"
    assert phenotype_result["status"] == "error"


def test_orpha_code_exists_helper_is_lenient_on_network_error():
    """A transient network failure on the existence-check itself must not
    block a request that would otherwise succeed -- treat "can't tell" as
    "proceed", matching the tool's existing resilience pattern elsewhere."""
    import requests

    tool = _tool()

    def fake_get(url, **kwargs):
        raise requests.exceptions.ConnectionError("boom")

    with patch("tooluniverse.orphanet_tool.requests.get", side_effect=fake_get):
        assert tool._orpha_code_exists("586") is True
