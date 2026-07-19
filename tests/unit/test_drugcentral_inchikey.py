"""Regression guard for Fix-R25E-1: DrugCentralTool's "inchikey" field
silently fell back to MyChem.info's internal "_id" whenever the real
drugcentral.structures.inchikey was absent -- confirmed live for
pembrolizumab (a monoclonal antibody with no small-molecule structure,
hence no InChIKey upstream), which returned "DPT0O3T46P" and
"CHEMBL3137343" as "inchikey" for two different records, neither a valid
InChIKey. Fixed by reporting None instead of a mislabeled internal ID,
and (for the search path) deduplicating on "_id" directly rather than on
the now-frequently-None inchikey value.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.drugcentral_tool import DrugCentralTool

pytestmark = pytest.mark.unit

_BIOLOGIC_SEARCH_RESPONSE = {
    "total": 2,
    "hits": [
        {
            "_id": "CHEMBL3137343",
            "drugcentral": {
                "structures": {"inn": "pembrolizumab"},
                "xrefs": {"chembl_id": "CHEMBL3137343"},
                "approval": ["FDA"],
            },
        },
        {
            "_id": "DPT0O3T46P",
            "drugcentral": {
                "structures": {"inn": "pembrolizumab"},
                "xrefs": {"chembl_id": "CHEMBL3137343"},
                "approval": ["FDA"],
            },
        },
    ],
}

_SMALL_MOLECULE_SEARCH_RESPONSE = {
    "total": 1,
    "hits": [
        {
            "_id": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N",
            "drugcentral": {
                "structures": {
                    "inn": "acetylsalicylic acid",
                    "inchikey": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N",
                },
                "xrefs": {},
                "approval": ["FDA"],
            },
        }
    ],
}

_GET_DRUG_RESPONSE = {
    "_id": "DPT0O3T46P",
    "drugcentral": {
        "structures": {"inn": "pembrolizumab"},
        "drug_use": {},
        "approval": ["FDA"],
    },
}


def _tool(operation):
    return DrugCentralTool(
        {"name": "drugcentral_test", "fields": {"operation": operation}}
    )


def _resp(json_body, status_code=200):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_body
    r.raise_for_status = MagicMock()
    return r


class TestSearchInchikey:
    def test_biologic_reports_none_not_internal_id(self):
        tool = _tool("search")
        resp = _resp(_BIOLOGIC_SEARCH_RESPONSE)

        with patch("tooluniverse.drugcentral_tool.requests.get", return_value=resp):
            result = tool.run({"query": "pembrolizumab"})

        assert result["status"] == "success"
        inchikeys = [r["inchikey"] for r in result["data"]]
        assert inchikeys == [None, None]
        assert len(result["data"]) == 2  # dedup by _id, not by (now-None) inchikey

    def test_small_molecule_still_returns_real_inchikey(self):
        tool = _tool("search")
        resp = _resp(_SMALL_MOLECULE_SEARCH_RESPONSE)

        with patch("tooluniverse.drugcentral_tool.requests.get", return_value=resp):
            result = tool.run({"query": "aspirin"})

        assert result["data"][0]["inchikey"] == "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"


class TestGetDrugInchikey:
    def test_get_drug_biologic_reports_none(self):
        tool = _tool("get_drug")
        resp = _resp(_GET_DRUG_RESPONSE)

        with patch("tooluniverse.drugcentral_tool.requests.get", return_value=resp):
            result = tool.run({"chem_id": "DPT0O3T46P"})

        assert result["status"] == "success"
        assert result["data"]["inchikey"] is None
