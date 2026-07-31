"""Regression guard for Fix-R4B-1: gwas_get_variants_for_trait returned an
UNSORTED page.

GWASVariantsForTrait and GWASAssociationsForTrait hit the same
/v2/associations endpoint, but only the latter sent sort=p_value&direction=asc.
The GWAS Catalog returns associations unsorted, so the variants tool handed
back an arbitrary slice: confirmed live that efo_id=MONDO_0004979 (asthma,
3219 associations) yielded p-values 2e-06 .. 2e-24 from this tool while the
sibling returned 7e-288, 8e-223, 2e-156 for the identical query. Every
genome-wide-significant locus was missing from the first page.
"""

from unittest.mock import patch

import pytest

from tooluniverse.gwas_tool import GWASAssociationsForTrait, GWASVariantsForTrait

pytestmark = pytest.mark.unit


def _params_for(cls, name, arguments):
    """Run the tool with the network stubbed and return the query params sent."""
    captured = {}

    def fake_request(endpoint, params):
        captured["params"] = params
        return {"_embedded": {"associations": []}, "page": {"totalElements": 0}}

    with patch.object(cls, "_make_request", side_effect=fake_request):
        cls({"name": name}).run(arguments)
    return captured["params"]


def _variant_params(arguments):
    return _params_for(
        GWASVariantsForTrait, "gwas_get_variants_for_trait", arguments
    )


def test_defaults_to_significance_order():
    params = _variant_params({"efo_id": "MONDO_0004979"})
    assert params["sort"] == "p_value"
    assert params["direction"] == "asc"


def test_explicit_sort_and_direction_are_respected():
    params = _variant_params(
        {"efo_id": "MONDO_0004979", "sort": "or_value", "direction": "desc"}
    )
    assert params["sort"] == "or_value"
    assert params["direction"] == "desc"


def test_matches_sibling_tool_ordering_for_the_same_trait():
    """The two trait tools query one endpoint; they must not disagree on order."""
    variants = _variant_params({"efo_id": "MONDO_0004979"})
    associations = _params_for(
        GWASAssociationsForTrait,
        "gwas_get_associations_for_trait",
        {"efo_id": "MONDO_0004979"},
    )
    assert (variants["sort"], variants["direction"]) == (
        associations["sort"],
        associations["direction"],
    )


def test_paging_and_size_still_pass_through():
    params = _variant_params({"efo_id": "MONDO_0004979", "size": 25, "page": 3})
    assert params["size"] == 25
    assert params["page"] == 3
