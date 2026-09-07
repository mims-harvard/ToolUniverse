"""HPA_get_cancer_prognostics_by_gene must report the assessed denominator.

Regression for Fix-R28B. The tool kept only the rows where `is_prognostic` is
true and reported `prognostic_cancers_count` with no denominator, so 5 rows came
back out of 31 cancer types HPA had actually assessed. A cancer type that HPA
tested and found NOT prognostic -- a citable negative result -- was
indistinguishable from a cancer type HPA has no data for at all.

Verified live against https://www.proteinatlas.org/ENSG00000253729.json (PRKDC):
31 'Cancer prognostics - ...' entries, 5 of them significant, with Head and Neck
Squamous Cell Carcinoma (TCGA) assessed at p = 2.86e-1 and absent from the old
output entirely.

The fix is additive: `prognostic_summary` still contains exactly the significant
rows it always did, and the non-significant rows go into a NEW
`non_prognostic_summary` key so a caller iterating the old array is unaffected.

All assertions run against a synthetic HPA JSON payload -- no network.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import tooluniverse  # noqa: E402
from tooluniverse.hpa_tool import HPAGetCancerPrognosticsTool  # noqa: E402

pytestmark = pytest.mark.unit

DATA_DIR = Path(tooluniverse.__file__).parent / "data"

PREFIX = "Cancer prognostics - "

# Mirrors the real PRKDC payload shape: `prognostic type` is "" and
# `is_prognostic` is False for assessed-but-not-significant cancers.
SIGNIFICANT = {
    "Kidney Renal Clear Cell Carcinoma (TCGA)": ("favorable", "3.76e-4"),
    "Liver Hepatocellular Carcinoma (TCGA)": ("unfavorable", "1.20e-4"),
    "Lung Adenocarcinoma (TCGA)": ("unfavorable", "6.38e-5"),
    "Pancreatic Adenocarcinoma (TCGA)": ("unfavorable", "5.55e-4"),
    "Rectum Adenocarcinoma (validation)": ("favorable", "5.18e-4"),
}
NOT_SIGNIFICANT = {
    "Head and Neck Squamous Cell Carcinoma (TCGA)": "2.86e-1",
    "Bladder Urothelial Carcinoma (TCGA)": "6.38e-2",
    "Breast Invasive Carcinoma (TCGA)": "3.76e-2",
    "Glioblastoma Multiforme (TCGA)": "4.05e-1",
    "Thyroid Carcinoma (TCGA)": "1.56e-2",
}


def _payload(**extra):
    data = {"Gene": "PRKDC", "Gene synonym": ["DNA-PKcs", "XRCC7"]}
    for cancer, (ptype, pval) in SIGNIFICANT.items():
        data[PREFIX + cancer] = {
            "prognostic type": ptype,
            "prognostic": ptype,
            "is_prognostic": True,
            "p_val": pval,
        }
    for cancer, pval in NOT_SIGNIFICANT.items():
        data[PREFIX + cancer] = {
            "prognostic type": "",
            "prognostic": "unprognostic",
            "is_prognostic": False,
            "p_val": pval,
        }
    data.update(extra)
    return data


def _run(payload):
    tool = HPAGetCancerPrognosticsTool(
        {"name": "HPA_get_cancer_prognostics_by_gene", "fields": {}}
    )
    with patch.object(tool, "_make_api_request", return_value=payload):
        result = tool.run({"ensembl_id": "ENSG00000253729"})
    assert result["status"] == "success"
    return result["data"]


def test_denominator_is_reported_alongside_the_significant_count():
    data = _run(_payload())

    assert data["prognostic_cancers_count"] == 5
    assert data["non_prognostic_cancers_count"] == 5
    assert data["cancers_assessed_count"] == 10
    assert (
        data["cancers_assessed_count"]
        == data["prognostic_cancers_count"] + data["non_prognostic_cancers_count"]
    )


def test_assessed_but_not_prognostic_cancer_is_reachable_with_its_p_value():
    """HNSCC was tested for PRKDC and found not prognostic; that is a result."""
    data = _run(_payload())

    hnscc = [
        row
        for row in data["non_prognostic_summary"]
        if row["cancer_type"] == "Head and Neck Squamous Cell Carcinoma (TCGA)"
    ]
    assert len(hnscc) == 1
    assert hnscc[0]["p_value"] == "2.86e-1"
    assert hnscc[0]["is_prognostic"] is False


def test_prognostic_summary_still_contains_only_significant_rows():
    """Additive: an existing caller iterating this array sees no new rows."""
    data = _run(_payload())

    assert len(data["prognostic_summary"]) == 5
    assert {row["cancer_type"] for row in data["prognostic_summary"]} == set(
        SIGNIFICANT
    )
    assert all(row["is_prognostic"] is True for row in data["prognostic_summary"])
    for row in data["prognostic_summary"]:
        assert set(row) == {
            "cancer_type",
            "prognostic_type",
            "p_value",
            "is_prognostic",
        }


def test_note_states_denominator_and_the_not_assessed_distinction():
    note = _run(_payload())["note"]

    assert "10" in note  # the denominator
    assert "non_prognostic_summary" in note
    assert "not assessed" in note.lower()


def test_unassessed_cancer_types_are_absent_from_both_arrays():
    """An empty dict means HPA has no data; it must not inflate the denominator."""
    data = _run(_payload(**{PREFIX + "Uveal Melanoma (TCGA)": {}}))

    listed = {row["cancer_type"] for row in data["prognostic_summary"]} | {
        row["cancer_type"] for row in data["non_prognostic_summary"]
    }
    assert "Uveal Melanoma (TCGA)" not in listed
    assert data["cancers_assessed_count"] == 10


def test_gene_with_no_significant_hits_still_reports_the_denominator():
    """The legacy string placeholder is preserved, but the denominator is real."""
    payload = {"Gene": "PRKDC", "Gene synonym": []}
    for cancer, pval in NOT_SIGNIFICANT.items():
        payload[PREFIX + cancer] = {
            "prognostic type": "",
            "prognostic": "unprognostic",
            "is_prognostic": False,
            "p_val": pval,
        }

    data = _run(payload)

    assert data["prognostic_cancers_count"] == 0
    assert isinstance(data["prognostic_summary"], str)  # unchanged legacy shape
    assert data["cancers_assessed_count"] == 5
    assert len(data["non_prognostic_summary"]) == 5


def test_config_documents_the_new_keys():
    configs = json.loads((DATA_DIR / "hpa_tools.json").read_text())
    cfg = next(c for c in configs if c["name"] == "HPA_get_cancer_prognostics_by_gene")
    props = cfg["return_schema"]["properties"]

    assert props["cancers_assessed_count"]["type"] == "integer"
    assert props["non_prognostic_cancers_count"]["type"] == "integer"
    assert props["non_prognostic_summary"]["type"] == "array"
    assert "significant" in props["prognostic_summary"]["description"].lower()
