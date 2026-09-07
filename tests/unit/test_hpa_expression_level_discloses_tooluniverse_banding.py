"""HPA responses must mark `expression_level` as ToolUniverse's own banding.

Regression for Fix-R33. HPA's columns publish a bare nTPM/nCPM number; the five
`expression_level` bands are thresholds ToolUniverse invented (>50, >10, >1,
>0.1). The band was emitted with no marker, surrounded by keys that are genuine
HPA provenance:

    {"matched_tissue": ..., "expression_value": ..., "expression_level": ...,
     "expression_unit": ..., "source_field": "Tissue RNA - liver [nTPM]"}

`source_field` literally names an HPA column, so an unmarked "Very high" read as
HPA's own classification. It is not.

The fix is strictly additive: thresholds and level strings are unchanged, and a
new `expression_level_basis` field names ToolUniverse and spells out the exact
cut-offs. It is emitted once per response -- at the top of `data` for all three
affected tools, never repeated per row.

Deliberately makes no claim about HPA's own published classification scheme,
which is not established here.

All assertions run against synthetic HPA payloads -- no network.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

import tooluniverse
from tooluniverse.hpa_tool import (
    HPA_CONTEXTUAL_EXPRESSION_BANDING,
    HPA_EXPRESSION_BANDING,
    HPA_EXPRESSION_BANDING_TITLE,
    HPAGetContextualBiologicalProcessTool,
    HPAGetRnaExpressionBySourceTool,
    HPAGetRnaExpressionByTissueTool,
)

pytestmark = pytest.mark.unit

CONFIGS = json.loads(
    (Path(tooluniverse.__file__).parent / "data" / "hpa_tools.json").read_text()
)


def _config(name):
    return next(c for c in CONFIGS if c["name"] == name)


def _run_tissue(tissues=("cerebral cortex", "liver")):
    tool = HPAGetRnaExpressionByTissueTool(
        {"name": "HPA_get_rna_expression_in_specific_tissues", "fields": {}}
    )
    panel = {
        "cerebral cortex": ("147.9", "Tissue RNA - cerebral cortex [nTPM]"),
        "liver": ("0.6", "Tissue RNA - liver [nTPM]"),
    }
    record = {
        "Gene": "MAPT",
        "Gene synonym": ["tau"],
        "RNA tissue specific nTPM": {"brain": 147.9},
    }
    with (
        patch.object(tool, "_make_api_request", return_value=record),
        patch.object(
            tool,
            "_fetch_tissue_panel",
            return_value={t: panel[t] for t in tissues if t in panel},
        ),
    ):
        result = tool.run(
            {"ensembl_id": "ENSG00000186868", "tissue_names": list(tissues)}
        )
    assert result["status"] == "success"
    return result["data"]


def _run_source(value="0.6", label="Tissue RNA - liver [nTPM]", source_type="tissue"):
    tool = HPAGetRnaExpressionBySourceTool(
        {"name": "HPA_get_rna_expression_by_source", "fields": {}}
    )
    with patch.object(tool, "_query_source_column", return_value=(value, label)):
        result = tool.run(
            {
                "gene_name": "MAPT",
                "source_type": source_type,
                "source_name": "liver" if source_type == "tissue" else "hepatocytes",
            }
        )
    assert result["status"] == "success"
    return result["data"]


def _run_contextual(ntpm=147.9):
    tool = HPAGetContextualBiologicalProcessTool(
        {"name": "HPA_get_contextual_biological_process_analysis", "fields": {}}
    )
    gene_row = [
        {
            "Gene": "MAPT",
            "Ensembl": "ENSG00000186868",
            "Gene synonym": ["tau"],
            "Biological process": "Neurogenesis, Transport",
        }
    ]
    json_record = {"RNA tissue specific nTPM": {"liver": ntpm}}
    # `_validate_context` is left real -- 'liver' is one of its valid tissues.
    with (
        patch(
            "tooluniverse.hpa_tool.HPASearchApiTool._make_api_request",
            return_value=gene_row,
        ),
        patch(
            "tooluniverse.hpa_tool.HPAJsonApiTool._make_api_request",
            return_value=json_record,
        ),
    ):
        result = tool.run({"gene_name": "MAPT", "context_name": "liver"})
    assert result["status"] == "success"
    return result["data"]


def test_thresholds_and_labels_are_unchanged():
    """The fix is a disclosure, not a re-banding."""
    assert HPA_EXPRESSION_BANDING.bands == (
        (50, "very high"),
        (10, "high"),
        (1, "medium"),
        (0.1, "low"),
    )
    assert HPA_EXPRESSION_BANDING.floor == "very low"
    assert HPA_EXPRESSION_BANDING.unknown == "unknown"
    # The title-cased variant must stay derived, never independently edited.
    assert HPA_EXPRESSION_BANDING_TITLE == HPA_EXPRESSION_BANDING.titled()
    assert HPA_EXPRESSION_BANDING_TITLE.categorize("147.9") == "Very high"
    assert HPA_EXPRESSION_BANDING_TITLE.categorize(None) == "Unknown"
    # The contextual tool keeps its own distinct vocabulary and cut-offs.
    assert HPA_CONTEXTUAL_EXPRESSION_BANDING.bands == (
        (10, "highly expressed"),
        (1, "moderately expressed"),
        (0.1, "expressed at low level"),
    )
    assert HPA_CONTEXTUAL_EXPRESSION_BANDING.floor == "not expressed or very low"


def test_tissue_response_discloses_the_banding_once_at_the_top_level():
    data = _run_tissue()
    basis = data["expression_level_basis"]

    assert "ToolUniverse" in basis
    assert "not a classification reported by HPA" in basis
    for fragment in (">50 = Very high", ">10 = High", ">1 = Medium", ">0.1 = Low"):
        assert fragment in basis
    assert "<=0.1 = Very low" in basis
    assert "nTPM" in basis
    # Stated once, not stamped on every row.
    assert all(
        "expression_level_basis" not in row
        for row in data["tissue_expression"].values()
    )


def test_tissue_rows_keep_their_hpa_provenance_keys_untouched():
    """Additive: the genuine-HPA keys beside expression_level are unchanged."""
    rows = _run_tissue()["tissue_expression"]

    cortex = rows["cerebral cortex"]
    assert cortex["expression_level"] == "Very high"
    assert cortex["source_field"] == "Tissue RNA - cerebral cortex [nTPM]"
    assert cortex["expression_value"] == "147.9"
    assert cortex["expression_unit"] == "nTPM"
    assert rows["liver"]["expression_level"] == "Low"


def test_tissue_no_data_rows_are_left_alone():
    """'No data' is already honest; it gets no threshold disclosure."""
    rows = _run_tissue(tissues=("cerebral cortex", "not_a_tissue"))["tissue_expression"]

    missing = rows["not_a_tissue"]
    assert missing["expression_level"] == "No data"
    assert missing["expression_value"] == "N/A"
    assert "expression_level_basis" not in missing


def test_tissue_response_omits_the_basis_when_nothing_was_banded():
    """No band was applied, so there are no cut-offs to disclose."""
    data = _run_tissue(tissues=("not_a_tissue",))

    assert data["tissue_expression"]["not_a_tissue"]["expression_level"] == "No data"
    assert "expression_level_basis" not in data


def test_by_source_response_carries_the_basis_next_to_the_level():
    data = _run_source()

    assert data["expression_level"] == "low"
    basis = data["expression_level_basis"]
    assert "ToolUniverse" in basis
    assert "not a classification reported by HPA" in basis
    for fragment in (">50 = very high", ">10 = high", ">1 = medium", ">0.1 = low"):
        assert fragment in basis
    assert "<=0.1 = very low" in basis


def test_by_source_basis_quotes_the_unit_hpa_actually_used():
    """single_cell columns are nCPM; the disclosure must not say nTPM there."""
    data = _run_source(
        value="81391.2",
        label="Single Cell Type RNA - Hepatocytes [nCPM]",
        source_type="single_cell",
    )

    assert data["expression_unit"] == "nCPM"
    assert data["expression_level"] == "very high"
    assert "nCPM value" in data["expression_level_basis"]
    assert "nTPM value" not in data["expression_level_basis"]


def test_basis_is_omitted_when_no_band_could_be_assigned():
    """An 'unknown' level has no thresholds to disclose."""
    data = _run_source(value="N/A")

    assert data["expression_level"] == "unknown"
    assert "expression_level_basis" not in data


def test_contextual_analysis_discloses_its_own_distinct_cutoffs():
    """This tool bands with a different vocabulary and has no >50 tier."""
    data = _run_contextual()

    assert data["expression_level"] == "highly expressed"
    basis = data["expression_level_basis"]
    assert "ToolUniverse" in basis
    assert "not a classification reported by HPA" in basis
    for fragment in (
        ">10 = highly expressed",
        ">1 = moderately expressed",
        ">0.1 = expressed at low level",
    ):
        assert fragment in basis
    assert "<=0.1 = not expressed or very low" in basis
    assert ">50" not in basis


def test_contextual_analysis_bands_and_verdict_are_unchanged():
    """The verdict derived from the band must read exactly as it did before."""
    assert (
        _run_contextual(147.9)["functional_relevance"] == "may be functionally relevant"
    )
    low = _run_contextual(0.05)
    assert low["expression_level"] == "not expressed or very low"
    assert low["functional_relevance"] == "is likely not functionally relevant"
    assert "not expressed or very low in liver" in low["contextual_conclusion"]


def test_basis_makes_no_claim_about_hpas_own_classification():
    """HPA's published scheme was not verified here, so nothing may assert it."""
    for basis in (
        _run_tissue()["expression_level_basis"],
        _run_source()["expression_level_basis"],
        _run_contextual()["expression_level_basis"],
    ):
        lowered = basis.lower()
        assert "hpa classifies" not in lowered
        assert "hpa's classification" not in lowered
        assert "matches hpa" not in lowered


@pytest.mark.parametrize(
    "name,banding",
    [
        ("HPA_get_rna_expression_in_specific_tissues", HPA_EXPRESSION_BANDING_TITLE),
        ("HPA_get_rna_expression_by_source", HPA_EXPRESSION_BANDING),
        (
            "HPA_get_contextual_biological_process_analysis",
            HPA_CONTEXTUAL_EXPRESSION_BANDING,
        ),
    ],
)
def test_configs_document_expression_level_as_tool_computed(name, banding):
    out = _config(name)["output_description"]

    assert "computed by ToolUniverse" in out
    assert "NOT a classification published by HPA" in out
    assert "expression_level_basis" in out
    # The prose quotes the cut-offs, so pin it to the constants: a re-banding
    # that forgets the description fails here instead of shipping a lie.
    for cutoff, label in banding.bands:
        assert f">{cutoff} {label}" in out
    assert f"<={banding.bands[-1][0]} {banding.floor}" in out


def test_gene_page_details_expression_level_is_not_relabelled():
    """That tool's expression_level comes from HPA's own XML <level>, not us."""
    cfg = _config("HPA_get_comprehensive_gene_details_by_ensembl_id")
    assert "computed by ToolUniverse" not in cfg["output_description"]
