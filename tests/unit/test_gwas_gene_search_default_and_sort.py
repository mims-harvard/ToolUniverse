"""Unit test: GWAS_search_associations_by_gene default size + p-value sort.

Regression: the tool defaulted to size=5 and returned the API's UNSORTED
associations. For a well-studied gene (TCF7L2, 902 associations) the 5 rows were
arbitrary -- all anthropometric (hip/waist/BMI) -- silently hiding the gene's
flagship type-2-diabetes associations, misleading a clinician. The default is
now 100 and the returned set is sorted by p-value (most significant first).
"""
import glob
import json
from unittest.mock import patch

import pytest

from tooluniverse.genomics_gene_search_tool import GWASGeneSearch


def _tool():
    return GWASGeneSearch({"name": "GWAS_search_associations_by_gene"})


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


@pytest.mark.unit
def test_default_size_is_100_not_5():
    captured = {}

    def fake_get(url, params=None, timeout=None):
        captured["params"] = params
        return _Resp({"_embedded": {"associations": []}, "page": {"totalElements": 0}})

    tool = _tool()
    with patch.object(tool.session, "get", side_effect=fake_get):
        tool.run({"gene_name": "TCF7L2"})
    assert captured["params"]["size"] == 100


@pytest.mark.unit
def test_associations_sorted_by_pvalue_most_significant_first():
    payload = {
        "_embedded": {
            "associations": [
                {"reported_trait": "BMI", "p_value": "2e-9"},
                {"reported_trait": "type 2 diabetes", "p_value": "1e-77"},
                {"reported_trait": "height", "p_value": None},
                {"reported_trait": "waist", "p_value": "5e-12"},
            ]
        },
        "page": {"totalElements": 4},
    }
    tool = _tool()
    with patch.object(tool.session, "get", return_value=_Resp(payload)):
        result = tool.run({"gene_name": "TCF7L2"})
    pvals = [a["p_value"] for a in result["associations"]]
    # Most significant (smallest) first; None/unparseable last.
    assert pvals == ["1e-77", "5e-12", "2e-9", None]
    assert result["associations"][0]["reported_trait"] == "type 2 diabetes"


@pytest.mark.unit
def test_config_default_size_is_100():
    for f in glob.glob("src/tooluniverse/data/*.json"):
        try:
            data = json.load(open(f))
        except ValueError:
            continue
        if isinstance(data, list):
            for t in data:
                if (
                    isinstance(t, dict)
                    and t.get("name") == "GWAS_search_associations_by_gene"
                ):
                    assert t["parameter"]["properties"]["size"]["default"] == 100
                    return
    raise AssertionError("GWAS_search_associations_by_gene config not found")
