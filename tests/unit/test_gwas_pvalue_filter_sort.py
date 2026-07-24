"""Unit test: gwas_search_associations p-value threshold fetches most-significant first.

Regression: the p_value threshold is applied CLIENT-SIDE to the fetched page, but
the GWAS Catalog API returns associations UNSORTED. So a strict threshold filtered
an arbitrary window and falsely returned 0 -- SLE p<=1e-100 -> 0 even though the
catalog has hits at p=2e-298. When a p-value filter is requested and no explicit
sort is given, the tool now sorts by p_value ascending so the fetched window holds
the strongest loci.
"""
from unittest.mock import patch

import pytest

from tooluniverse.gwas_tool import GWASAssociationSearch


def _tool():
    return GWASAssociationSearch({"name": "gwas_search_associations"})


def _params_for(arguments):
    captured = {}

    def fake_request(endpoint, params):
        captured["params"] = params
        return {"_embedded": {"associations": []}, "page": {"totalElements": 0}}

    with patch.object(GWASAssociationSearch, "_make_request", side_effect=fake_request):
        _tool().run(arguments)
    return captured["params"]


@pytest.mark.unit
def test_pvalue_filter_injects_significance_sort():
    params = _params_for({"efo_trait": "systemic lupus erythematosus", "p_value": 1e-100})
    assert params.get("sort") == "p_value"
    assert params.get("direction") == "asc"


@pytest.mark.unit
def test_explicit_sort_is_respected_over_default():
    params = _params_for(
        {"efo_trait": "x", "p_value": 1e-8, "sort": "or_value", "direction": "desc"}
    )
    assert params["sort"] == "or_value"
    assert params["direction"] == "desc"


@pytest.mark.unit
def test_no_pvalue_filter_leaves_sort_unset():
    params = _params_for({"efo_trait": "x"})
    assert "sort" not in params
