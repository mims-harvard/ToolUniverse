"""Regression guard for Fix-R31 (HPA column codes, units and tissue counts).

HPA's search_download.php SILENTLY DROPS column codes it does not recognise,
so a wrong code is byte-identical to "this gene has no data" -- and the tool
blamed the caller. Three consequences, all verified live:

1. `t_RNA_skin` does not exist; HPA publishes the tissue as `t_RNA_skin_1`
   ("Tissue RNA - skin 1 [nTPM]"), so every 'skin' query was reported as an
   unrecognized tissue name. Confirmed against the live API:
     ?search=NCSTN&columns=g,eg,t_RNA_skin_1,t_RNA_skin,t_RNA_liver ->
     [{"Gene":"NCSTN","Ensembl":"ENSG00000162736",
       "Tissue RNA - liver [nTPM]":"48.9",
       "Tissue RNA - skin 1 [nTPM]":"34.4"}]      <- no "skin" key at all
   'stomach' (`stomach_1`) and 'endometrium' (`endometrium_1`) had the same
   defect.
2. `rnascm` and `rnablm` are not column codes at all, so source_type
   'single_cell' and 'blood' were 100% dead. The real per-source columns are
   `sc_RNA_<CellType>` and `blood_RNA_<CellType>`.
3. `expression_unit` was hard-coded to "nTPM" even for single cell data,
   which HPA reports in nCPM ("Single Cell Type RNA - Hepatocytes [nCPM]").

Plus: HPA_get_comprehensive_gene_details_by_ensembl_id reported
"tissues_with_expression": 184 for NCSTN -- a raw row count of a
tissue x antibody array in which 135 rows had no level, 9 said "not detected"
and "Skin 1" appeared 4 times. HPA publishes ~44 consensus tissues, so the
number was impossible on its face.

All fixtures below are the exact response shapes returned by the live API.
No network access is performed.
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.hpa_tool import (
    HPA_TISSUE_COLUMN_ALIASES,
    HPA_UNAVAILABLE_SOURCES,
    HPAGetGenePageDetailsTool,
    HPAGetRnaExpressionBySourceTool,
    HPAGetRnaExpressionByTissueTool,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def json(self):
        return self._payload


# HPA's /{ensembl_id}.json record for NCSTN. The enrichment summary is empty
# for a broadly-expressed gene -- which is exactly why the per-tissue columns
# have to work.
_NCSTN_JSON = {
    "Gene": "NCSTN",
    "Gene synonym": ["APH2", "KIAA0253"],
    "Ensembl": "ENSG00000162736",
    "RNA tissue specific nTPM": {},
}

# Live: ?search=NCSTN&columns=g,eg,t_RNA_skin_1,t_RNA_skin,t_RNA_liver
# -- note HPA returned no key whatsoever for the bogus `t_RNA_skin`.
_NCSTN_TISSUE_PANEL = [
    {
        "Gene": "NCSTN",
        "Ensembl": "ENSG00000162736",
        "Tissue RNA - liver [nTPM]": "48.9",
        "Tissue RNA - skin 1 [nTPM]": "34.4",
    }
]


def _tissue_tool():
    return HPAGetRnaExpressionByTissueTool(
        {"name": "HPA_get_rna_expression_in_specific_tissues", "fields": {}}
    )


def _source_tool():
    return HPAGetRnaExpressionBySourceTool(
        {"name": "HPA_get_rna_expression_by_source", "fields": {}}
    )


def _run_tissue_query(tissue_names):
    """Run the tissue tool offline, returning (data, requested column strings)."""
    tool = _tissue_tool()
    requested = []

    def fake_get(url, **kwargs):
        params = kwargs.get("params") or {}
        if "search_download.php" in url:
            requested.append(params.get("columns", ""))
            return _FakeResponse(_NCSTN_TISSUE_PANEL)
        return _FakeResponse(_NCSTN_JSON)

    with patch("tooluniverse.hpa_tool.requests.get", side_effect=fake_get):
        result = tool.run(
            {"ensembl_id": "ENSG00000162736", "tissue_names": tissue_names}
        )
    assert result["status"] == "success", result
    return result["data"], requested


# ---------------------------------------------------------------------------
# 1. 'skin' resolves to HPA's real `t_RNA_skin_1` column
# ---------------------------------------------------------------------------


def test_skin_reads_the_skin_1_column_and_is_not_called_unrecognized():
    data, requested = _run_tissue_query(["skin", "liver"])
    skin = data["tissue_expression"]["skin"]

    assert skin["expression_value"] == "34.4"
    assert skin["source_field"] == "Tissue RNA - skin 1 [nTPM]"
    assert skin["matched_tissue"] != "Not found"
    # The old failure mode: blaming the caller's tissue name.
    assert "unrecognized" not in skin.get("note", "").lower()
    # ...and the request must actually ask for the column HPA has.
    assert any("t_RNA_skin_1" in c for c in requested)


def test_skin_column_alias_is_pinned_to_the_real_hpa_suffix():
    assert HPA_TISSUE_COLUMN_ALIASES["skin"] == ["skin_1"]
    assert HPA_TISSUE_COLUMN_ALIASES["stomach"] == ["stomach_1"]
    assert HPA_TISSUE_COLUMN_ALIASES["endometrium"] == ["endometrium_1"]


def test_tissue_without_an_hpa_rna_column_says_so_instead_of_blaming_the_name():
    # HPA covers bronchus only in its protein/IHC atlas: t_RNA_bronchus is
    # dropped by the API, exactly like a typo would be.
    assert "bronchus" in HPA_UNAVAILABLE_SOURCES["tissue"]
    data, _ = _run_tissue_query(["bronchus"])
    note = data["tissue_expression"]["bronchus"]["note"]
    assert "protein/IHC" in note
    assert "unrecognized" not in note.lower()


# ---------------------------------------------------------------------------
# 2. liver is unchanged
# ---------------------------------------------------------------------------


def test_liver_is_unchanged():
    data, _ = _run_tissue_query(["skin", "liver"])
    liver = data["tissue_expression"]["liver"]

    assert liver["expression_value"] == "48.9"
    assert liver["matched_tissue"] == "liver"
    assert liver["expression_level"] == "High"
    assert liver["source_field"] == "Tissue RNA - liver [nTPM]"
    assert liver["expression_unit"] == "nTPM"
    assert "note" not in liver


# ---------------------------------------------------------------------------
# 3. single_cell / blood return data, with the unit HPA actually used
# ---------------------------------------------------------------------------


def test_single_cell_returns_hepatocyte_value_in_nCPM():
    tool = _source_tool()
    requested = []

    # Live: ?search=ALB&columns=g,eg,rnascm,sc_RNA_Hepatocytes ->
    # [{"Gene":"ALB","Ensembl":"ENSG00000163631",
    #   "Single Cell Type RNA - Hepatocytes [nCPM]":"81391.2"}]  (no "rnascm")
    def fake_request(gene, columns, format_type="json"):
        requested.append(columns)
        if "sc_RNA_Hepatocytes" in columns:
            return [
                {
                    "Gene": "ALB",
                    "Ensembl": "ENSG00000163631",
                    "Single Cell Type RNA - Hepatocytes [nCPM]": "81391.2",
                }
            ]
        # HPA drops `rnascm` entirely -- the row comes back with no data key.
        return [{"Gene": "ALB"}]

    with patch.object(tool, "_make_api_request", side_effect=fake_request):
        result = tool.run(
            {
                "gene_name": "ALB",
                "source_type": "single_cell",
                "source_name": "hepatocyte",
            }
        )

    data = result["data"]
    assert data["expression_value"] == "81391.2"
    # HPA reports single cell data in nCPM, not nTPM.
    assert data["expression_unit"] == "nCPM"
    assert data["column_queried"] == "Single Cell Type RNA - Hepatocytes [nCPM]"
    assert data["status"] == "ok"
    assert any("sc_RNA_Hepatocytes" in c for c in requested)
    assert not any(c.endswith("rnascm") for c in requested)


def test_blood_returns_t_reg_value_in_nTPM():
    tool = _source_tool()
    requested = []

    # Live: ?search=CD3E&columns=g,rnablm,blood_RNA_T-reg,rnabcs ->
    # [{"Gene":"CD3E","RNA blood cell specificity":"Group enriched",
    #   "Blood RNA - T-reg [nTPM]":"427.4"}]      (no "rnablm" key)
    def fake_request(gene, columns, format_type="json"):
        requested.append(columns)
        if "blood_RNA_T-reg" in columns:
            return [{"Gene": "CD3E", "Blood RNA - T-reg [nTPM]": "427.4"}]
        return [{"Gene": "CD3E"}]

    with patch.object(tool, "_make_api_request", side_effect=fake_request):
        result = tool.run(
            {"gene_name": "CD3E", "source_type": "blood", "source_name": "t_cell"}
        )

    data = result["data"]
    assert data["expression_value"] == "427.4"
    assert data["expression_unit"] == "nTPM"
    assert data["column_queried"] == "Blood RNA - T-reg [nTPM]"
    assert data["status"] == "ok"
    assert any("blood_RNA_T-reg" in c for c in requested)
    assert not any(c.endswith("rnablm") for c in requested)
    # HPA's blood atlas has no aggregate T-cell column, so say which subset
    # the number is instead of passing it off as "t_cell".
    assert "T-reg" in data["note"]


# ---------------------------------------------------------------------------
# 4. tissues_with_expression counts detected tissues, not assay rows
# ---------------------------------------------------------------------------


_GENE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<proteinAtlas>
  <entry>
    <name>NCSTN</name>
    <tissueExpression>
      <data>
        <tissue organ="Skin">Skin 1</tissue>
        <level type="expression">medium</level>
      </data>
      <data>
        <tissue organ="Skin">Skin 1</tissue>
        <level type="expression">medium</level>
      </data>
      <data>
        <tissue organ="Skin">Skin 1</tissue>
        <level type="expression">medium</level>
      </data>
      <data>
        <tissue organ="Skin">Skin 1</tissue>
        <level type="expression">medium</level>
      </data>
      <data>
        <tissue organ="Kidney &amp; urinary bladder">Kidney</tissue>
        <level type="expression">high</level>
      </data>
      <data>
        <tissue organ="Liver &amp; gallbladder">Liver</tissue>
        <level type="expression">not detected</level>
      </data>
      <data>
        <tissue organ="Connective &amp; soft tissue">Adipose tissue</tissue>
      </data>
    </tissueExpression>
  </entry>
</proteinAtlas>
"""


def _parse_summary():
    tool = HPAGetGenePageDetailsTool(
        {"name": "HPA_get_comprehensive_gene_details_by_ensembl_id", "fields": {}}
    )
    root = ET.fromstring(_GENE_XML)
    parsed = tool._parse_gene_xml(root, "ENSG00000162736", False, False, True)
    return parsed


def test_summary_counts_only_distinct_tissues_with_detected_expression():
    parsed = _parse_summary()
    summary = parsed["summary"]

    # 7 assay rows / 4 distinct tissues, of which only Skin 1 and Kidney have
    # a detected level ("not detected" and the blank row do not count).
    assert summary["tissues_with_expression"] == 2
    assert summary["distinct_tissues_assayed"] == 4
    assert summary["tissue_expression_rows"] == 7
    assert len(parsed["tissue_expression"]) == 7


def test_summary_note_explains_the_denominator():
    summary = _parse_summary()["summary"]
    assert "not detected" in summary["summary_note"]
    assert "tissue_expression_rows" in summary["summary_note"]


def test_count_tissues_helper_ignores_blank_and_not_detected():
    count = HPAGetGenePageDetailsTool._count_tissues
    rows = [
        {"tissue_name": "Skin 1", "expression_level": "expression: medium"},
        {"tissue_name": "Skin 1", "expression_level": "expression: medium"},
        {"tissue_name": "Liver", "expression_level": "expression: not detected"},
        {"tissue_name": "Adipose tissue", "expression_level": ""},
        {"tissue_name": "", "expression_level": "expression: high"},
    ]
    assert count(rows) == (1, 3)
    assert count([]) == (0, 0)
