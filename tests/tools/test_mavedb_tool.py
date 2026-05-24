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


# ---------------------------------------------------------------------------
# MaveDB_get_effect_matrix — one-shot DMS loader
# ---------------------------------------------------------------------------


def _make_effect_matrix_tool(csv_text=None):
    """Tool wired to dispatch get_effect_matrix with mocked HTTP."""
    cfg = {
        "name": "MaveDB_get_effect_matrix",
        "fields": {"operation": "get_effect_matrix"},
    }
    tool = MaveDBTool(cfg)
    tool.session = MagicMock()
    if csv_text is not None:
        tool.session.get.return_value = _mock_response(csv_text)
    return tool


def test_effect_matrix_parses_missense_filters_others():
    """Verify HGVS filter drops non-missense and reshapes to (20, n_positions)."""
    csv_text = (
        "accession,hgvs_nt,hgvs_splice,hgvs_pro,score\n"
        # Single missense — kept
        "v1,NA,NA,p.Met1Ala,0.5\n"
        "v2,NA,NA,p.Met1Cys,-0.3\n"
        "v3,NA,NA,p.Thr2Ala,1.2\n"
        "v4,NA,NA,p.Thr2Val,2.5\n"
        # Synonymous — dropped
        "v5,NA,NA,p.Met1=,0.0\n"
        # Nonsense — dropped
        "v6,NA,NA,p.Met1*,-3.0\n"
        # Multi-mutant — dropped
        "v7,NA,NA,p.[Met1Ala;Thr2Gly],-1.0\n"
        # Parenthesized — kept
        "v8,NA,NA,p.(Lys3Arg),0.8\n"
    )
    tool = _make_effect_matrix_tool(csv_text)
    result = tool.run({"urn": "urn:mavedb:test"})
    assert result["status"] == "success"
    d = result["data"]
    assert d["shape"] == [20, 3]
    assert d["positions"] == [1, 2, 3]
    assert d["amino_acid_order"] == "ACDEFGHIKLMNPQRSTVWY"
    assert d["n_parsed_single_missense"] == 5
    assert d["n_dropped"] == 3
    assert d["score_field_used"] == "score"

    # Spot-check matrix cells: row=alt_aa, col=position
    aa_index = {a: i for i, a in enumerate("ACDEFGHIKLMNPQRSTVWY")}
    assert d["matrix"][aa_index["A"]][0] == 0.5    # Met1Ala
    assert d["matrix"][aa_index["C"]][0] == -0.3   # Met1Cys
    assert d["matrix"][aa_index["V"]][1] == 2.5    # Thr2Val
    assert d["matrix"][aa_index["R"]][2] == 0.8    # Lys3Arg parenthesized


def test_effect_matrix_alternate_score_field():
    """Auto-detection picks 'ddG' when 'score' isn't present."""
    csv_text = (
        "accession,hgvs_pro,ddG\n"
        "v1,p.Met1Ala,0.42\n"
        "v2,p.Thr2Val,2.17\n"
    )
    tool = _make_effect_matrix_tool(csv_text)
    result = tool.run({"urn": "urn:mavedb:test"})
    assert result["status"] == "success"
    assert result["data"]["score_field_used"] == "ddG"


def test_effect_matrix_explicit_score_field():
    """If user passes score_field, that one is used."""
    csv_text = (
        "accession,hgvs_pro,score,fitness\n"
        "v1,p.Met1Ala,0.5,99\n"
    )
    tool = _make_effect_matrix_tool(csv_text)
    result = tool.run({"urn": "urn:mavedb:test", "score_field": "fitness"})
    assert result["data"]["score_field_used"] == "fitness"
    aa_index = {a: i for i, a in enumerate("ACDEFGHIKLMNPQRSTVWY")}
    assert result["data"]["matrix"][aa_index["A"]][0] == 99.0


def test_effect_matrix_no_usable_variants_errors():
    """All non-missense → tool returns explicit error, not empty matrix."""
    csv_text = (
        "accession,hgvs_pro,score\n"
        "v1,p.Met1=,0.0\n"
        "v2,p.Arg175*,-2.0\n"
    )
    tool = _make_effect_matrix_tool(csv_text)
    result = tool.run({"urn": "urn:mavedb:test"})
    assert result["status"] == "error"
    assert "single-missense" in result["error"].lower()


def test_effect_matrix_missing_urn():
    tool = _make_effect_matrix_tool()
    result = tool.run({})
    assert result["status"] == "error"
    assert "urn" in result["error"]


def test_effect_matrix_numbering_check_passes_when_uniprot_matches():
    """uniprot_id triggers landmark verification against canonical sequence."""
    # Mock both the MaveDB CSV and the UniProt FASTA lookup
    csv_text = (
        "accession,hgvs_pro,score\n"
        "v1,p.Met1Ala,0.5\n"
    )
    cfg = {
        "name": "MaveDB_get_effect_matrix",
        "fields": {"operation": "get_effect_matrix"},
    }
    tool = MaveDBTool(cfg)
    tool.session = MagicMock()

    def fake_get(url, *, timeout=None, **_kw):
        r = MagicMock()
        if "rest.uniprot.org" in url:
            r.status_code = 200
            # KRAS canonical starts with M
            r.text = ">sp|P01116|RASK_HUMAN dummy\nMTEYKLVVVGAGGVGKSALTIQLIQ\n"
        else:
            r.status_code = 200
            r.text = csv_text
        return r

    tool.session.get.side_effect = fake_get
    result = tool.run({"urn": "urn:mavedb:test", "uniprot_id": "P01116"})
    assert result["status"] == "success"
    assert result["data"]["numbering_offset"] == 0
    assert result["data"]["numbering_check"]["match"] is True


def test_effect_matrix_numbering_check_detects_offset():
    """If MaveDB position 1 has ref M but UniProt position 1 is X, detect offset."""
    csv_text = (
        "accession,hgvs_pro,score\n"
        "v1,p.Met5Ala,0.5\n"
    )
    cfg = {
        "name": "MaveDB_get_effect_matrix",
        "fields": {"operation": "get_effect_matrix"},
    }
    tool = MaveDBTool(cfg)
    tool.session = MagicMock()

    def fake_get(url, *, timeout=None, **_kw):
        r = MagicMock()
        if "rest.uniprot.org" in url:
            r.status_code = 200
            # In UniProt, position 5 = K (offset -2: M is at position 3)
            r.text = ">sp|TEST|TEST_HUMAN dummy\nXXMTEYKLVVVGAGGVGKSAL\n"
        else:
            r.status_code = 200
            r.text = csv_text
        return r

    tool.session.get.side_effect = fake_get
    result = tool.run({"urn": "urn:mavedb:test", "uniprot_id": "TEST"})
    assert result["status"] == "success"
    assert result["data"]["numbering_offset"] is not None
    assert result["data"]["numbering_check"]["match"] is False
    assert result["data"]["numbering_check"]["detected_offset"] == -2
