"""Regression guard for Fix-R14E-1: dbSNP's esummary.fcgi doesn't 404 or
omit the ID for a nonexistent rsID -- it returns a per-ID entry shaped
{"uid": "...", "error": "cannot get document summary"} (confirmed live via
raw curl to eutils.ncbi.nlm.nih.gov). The old code only checked whether the
rsid was a key in the result dict, so this error-shaped entry was treated as
a real record and every field defaulted to null/empty, silently returning
status:"success" for a variant that doesn't exist. Both
dbSNPGetVariantByRsID and dbSNPGetFrequencies shared this bug.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.dbsnp_tool import dbSNPGetVariantByRsID, dbSNPGetFrequencies

pytestmark = pytest.mark.unit

NOT_FOUND_RESPONSE = {
    "status": "success",
    "data": {
        "result": {
            "uids": ["99999999999999"],
            "99999999999999": {
                "uid": "99999999999999",
                "error": "cannot get document summary",
            },
        }
    },
}

FOUND_RESPONSE = {
    "status": "success",
    "data": {
        "result": {
            "uids": ["429358"],
            "429358": {
                "snp_id": 429358,
                "chr": "19",
                "chrpos": "19:44908684",
                "allele": "Y",
                "snp_class": "snv",
                "clinical_significance": "risk-factor",
                "genes": [{"name": "APOE"}],
                "global_mafs": [],
                "docsum": "",
                "spdi": "",
                "fxn_class": "missense_variant",
                "validated": "by-cluster",
                "createdate": "2000-01-01",
                "updatedate": "2020-01-01",
            },
        }
    },
}


def test_variant_by_rsid_reports_error_for_nonexistent_id(monkeypatch):
    tool = dbSNPGetVariantByRsID({"name": "dbsnp_get_variant_by_rsid"})
    monkeypatch.setattr(tool, "_make_request", lambda *a, **k: dict(NOT_FOUND_RESPONSE))

    result = tool.run({"rsid": "rs99999999999999"})

    assert result["status"] == "error"
    assert "not found" in result["error"]


def test_variant_by_rsid_still_succeeds_for_real_variant(monkeypatch):
    tool = dbSNPGetVariantByRsID({"name": "dbsnp_get_variant_by_rsid"})
    monkeypatch.setattr(tool, "_make_request", lambda *a, **k: dict(FOUND_RESPONSE))

    result = tool.run({"rsid": "rs429358"})

    assert result["status"] == "success"
    assert result["data"]["chromosome"] == "19"
    assert result["data"]["genes"] == ["APOE"]


def test_frequencies_reports_error_for_nonexistent_id(monkeypatch):
    tool = dbSNPGetFrequencies({"name": "dbsnp_get_frequencies"})
    monkeypatch.setattr(tool, "_make_request", lambda *a, **k: dict(NOT_FOUND_RESPONSE))

    result = tool.run({"rsid": "rs99999999999999"})

    assert result["status"] == "error"
    assert "not found" in result["error"]


def test_frequencies_still_succeeds_for_real_variant(monkeypatch):
    tool = dbSNPGetFrequencies({"name": "dbsnp_get_frequencies"})
    response = dict(FOUND_RESPONSE)
    response["data"]["result"]["429358"] = {
        **FOUND_RESPONSE["data"]["result"]["429358"],
        "global_mafs": [{"study": "1000Genomes", "freq": "C=0.15/754"}],
    }
    monkeypatch.setattr(tool, "_make_request", lambda *a, **k: response)

    result = tool.run({"rsid": "rs429358"})

    assert result["status"] == "success"
    assert result["data"]["total_studies"] == 1
