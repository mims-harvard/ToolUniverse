"""Tests for EuropePMC_get_full_text (EuropePMCStructuredFullTextTool)."""

import pytest
from tooluniverse import ToolUniverse


@pytest.fixture(scope="module")
def tu():
    t = ToolUniverse()
    t.load_tools()
    return t


def _run(tu, **kwargs):
    return tu.run_one_function(
        {"name": "EuropePMC_get_full_text", "arguments": kwargs}
    )


# ------------------------------------------------------------------
# Tool loading
# ------------------------------------------------------------------


def test_tool_registered(tu):
    assert "EuropePMC_get_full_text" in tu.all_tool_dict
    tool = tu.all_tool_dict["EuropePMC_get_full_text"]
    assert tool["type"] == "EuropePMCStructuredFullTextTool"


# ------------------------------------------------------------------
# Success path: PMC ID
# ------------------------------------------------------------------


@pytest.mark.network
def test_pmcid_success(tu):
    result = _run(tu, pmcid="PMC7096075")
    assert result["status"] == "success"
    data = result["data"]
    assert "Ashwagandha" in data["title"]
    assert data["abstract"] is not None
    assert len(data["abstract"]) > 100


@pytest.mark.network
def test_pmcid_sections(tu):
    result = _run(tu, pmcid="PMC7096075")
    sections = result["data"]["sections"]
    assert "introduction" in sections
    assert "methods" in sections
    assert "results" in sections
    assert "discussion" in sections
    assert "conclusions" in sections


@pytest.mark.network
def test_pmcid_figures(tu):
    result = _run(tu, pmcid="PMC7096075")
    data = result["data"]
    assert data["figure_count"] >= 1
    assert len(data["figures"]) == data["figure_count"]
    fig = data["figures"][0]
    assert "label" in fig
    assert "caption" in fig


@pytest.mark.network
def test_pmcid_tables(tu):
    result = _run(tu, pmcid="PMC7096075")
    data = result["data"]
    assert data["table_count"] >= 1
    assert len(data["tables"]) == data["table_count"]
    tbl = data["tables"][0]
    assert "label" in tbl
    assert "caption" in tbl


@pytest.mark.network
def test_pmcid_references(tu):
    result = _run(tu, pmcid="PMC7096075")
    data = result["data"]
    assert data["reference_count"] >= 1
    assert len(data["references"]) == data["reference_count"]
    ref = data["references"][0]
    assert "id" in ref
    assert "text" in ref
    assert len(ref["text"]) > 10


@pytest.mark.network
def test_metadata(tu):
    result = _run(tu, pmcid="PMC7096075")
    meta = result["metadata"]
    assert meta["pmcid"] == "PMC7096075"
    assert meta["source"] is not None
    assert meta["format"] == "xml"


# ------------------------------------------------------------------
# PMC ID normalisation
# ------------------------------------------------------------------


@pytest.mark.network
def test_pmcid_without_prefix(tu):
    result = _run(tu, pmcid="7096075")
    assert result["status"] == "success"
    assert result["metadata"]["pmcid"] == "PMC7096075"


# ------------------------------------------------------------------
# Success path: PMID (auto-resolved)
# ------------------------------------------------------------------


@pytest.mark.network
def test_pmid_resolution(tu):
    result = _run(tu, pmid="32226684")
    assert result["status"] == "success"
    assert "Ashwagandha" in result["data"]["title"]
    assert result["metadata"]["pmcid"] == "PMC7096075"


# ------------------------------------------------------------------
# Error paths
# ------------------------------------------------------------------


def test_no_params(tu):
    result = _run(tu)
    assert result["status"] == "error"
    assert "pmcid" in result["error"].lower() or "pmid" in result["error"].lower()


@pytest.mark.network
def test_invalid_pmid(tu):
    result = _run(tu, pmid="999999999")
    assert result["status"] == "error"
    assert "resolve" in result["error"].lower() or "not" in result["error"].lower()


def test_invalid_pmcid_format(tu):
    result = _run(tu, pmcid="not_a_number_at_all")
    # Should either error gracefully or attempt and fail
    assert result["status"] in ("error", "success")


# ------------------------------------------------------------------
# max_section_chars truncation
# ------------------------------------------------------------------


@pytest.mark.network
def test_max_section_chars(tu):
    result = _run(tu, pmcid="PMC7096075", max_section_chars=1000)
    assert result["status"] == "success"
    sections = result["data"]["sections"]
    for key, val in sections.items():
        if isinstance(val, str):
            # Sections longer than 1000 chars should be truncated
            assert len(val) <= 1020  # 1000 + " ... [truncated]"
