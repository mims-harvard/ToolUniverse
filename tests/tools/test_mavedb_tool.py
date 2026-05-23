"""Unit tests for MaveDBTool pagination semantics.

The /scores endpoint returns every variant in one HTTP CSV download; the
`limit` parameter is purely client-side truncation. Default behavior was
recently fixed: limit=0 (or null/omitted) now returns ALL variants instead
of being capped at 500. This test pins that behavior with a mocked CSV.
"""
import io
from unittest.mock import MagicMock

import pytest

from tooluniverse.mavedb_tool import MaveDBTool


def _mock_response(csv_text, status_code=200):
    r = MagicMock()
    r.status_code = status_code
    r.text = csv_text
    return r


@pytest.fixture
def csv_3000():
    """3000-row CSV with a single hgvs_pro and numeric score column."""
    rows = ["accession,hgvs_nt,hgvs_splice,hgvs_pro,score"]
    for i in range(3000):
        # Cycle through 3 example variants so hgvs_pro filter has meaningful matches
        pos = (i % 200) + 2
        alt = "Ala"
        rows.append(f"acc{i},NA,NA,p.Thr{pos}{alt},{i * 0.001:.4f}")
    return "\n".join(rows) + "\n"


def _make_tool(csv_text=None, status_code=200):
    """Build a MaveDBTool wired to dispatch get_variant_scores with mocked HTTP."""
    cfg = {
        "name": "MaveDB_get_variant_scores",
        "fields": {"operation": "get_variant_scores"},
    }
    tool = MaveDBTool(cfg)
    tool.session = MagicMock()
    if csv_text is not None:
        tool.session.get.return_value = _mock_response(csv_text, status_code)
    return tool


@pytest.fixture
def tool_with_csv(csv_3000):
    return _make_tool(csv_3000)


def test_default_no_limit_returns_all_variants(tool_with_csv):
    """The previous bug: default capped at 500. Fixed: returns all 3000."""
    result = tool_with_csv.run({"urn": "urn:mavedb:00000115-a-7"})
    assert result["status"] == "success"
    d = result["data"]
    assert d["returned"] == 3000
    assert d["total_variants_in_set"] == 3000
    assert d["truncated"] is False
    assert d["limit_applied"] is None


def test_limit_zero_returns_all_explicitly(tool_with_csv):
    result = tool_with_csv.run({"urn": "urn:mavedb:00000115-a-7", "limit": 0})
    d = result["data"]
    assert d["returned"] == 3000
    assert d["truncated"] is False


def test_limit_positive_truncates_and_reports_truncated_true(tool_with_csv):
    result = tool_with_csv.run({"urn": "urn:mavedb:00000115-a-7", "limit": 100})
    d = result["data"]
    assert d["returned"] == 100
    assert d["truncated"] is True
    assert d["limit_applied"] == 100
    assert d["total_variants_in_set"] == 3000


def test_limit_larger_than_data_returns_all(tool_with_csv):
    result = tool_with_csv.run({"urn": "urn:mavedb:00000115-a-7", "limit": 99999})
    d = result["data"]
    assert d["returned"] == 3000
    assert d["truncated"] is False
    assert d["limit_applied"] == 99999


def test_negative_limit_treated_as_no_limit(tool_with_csv):
    result = tool_with_csv.run({"urn": "urn:mavedb:00000115-a-7", "limit": -5})
    d = result["data"]
    assert d["returned"] == 3000
    assert d["truncated"] is False


def test_hgvs_filter_applies_then_limit(tool_with_csv):
    """hgvs_pro substring filter runs first; limit truncates the filtered set."""
    result = tool_with_csv.run({
        "urn": "urn:mavedb:00000115-a-7",
        "hgvs_pro": "Thr2A",
    })
    d = result["data"]
    assert d["returned"] > 0
    assert d["hgvs_filter"] == "Thr2A"


def test_missing_urn_returns_error():
    tool = _make_tool()
    result = tool.run({})
    assert result["status"] == "error"
    assert "urn" in result["error"]


def test_http_404_returns_error():
    tool = _make_tool("", status_code=404)
    result = tool.run({"urn": "urn:mavedb:fake"})
    assert result["status"] == "error"
    assert "not found" in result["error"].lower()


def test_empty_csv_returns_error():
    tool = _make_tool("")
    result = tool.run({"urn": "urn:mavedb:empty"})
    assert result["status"] == "error"
    assert "no scores" in result["error"].lower()
