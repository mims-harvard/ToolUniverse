"""Round-31 regression guards for src/tooluniverse/gwas_tool.py.

Issue 1 -- a client-side filter's zero result was blamed on the trait.
    gwas_search_associations '{"efo_id":"EFO_0004340","p_value":5e-08,
    "sort":"p_value","direction":"desc","size":10}' returned data=[] with a
    note telling the caller their EFO term was probably wrong -- in the same
    payload that reported pagination.totalElements=23608 for BMI, one of the
    best-populated traits in GWAS Catalog. The p_value threshold was never
    sent upstream; it was applied client-side to a page fetched
    direction=desc, i.e. the LEAST significant rows, so every row failed.

    The GWAS Catalog REST API v2 genuinely has no server-side p-value filter.
    Verified against its OpenAPI document
    (https://www.ebi.ac.uk/gwas/rest/api/v2/rest-api-doc.yaml): GET
    /v2/associations declares only pubmed_id, rs_id, full_pvalue_set,
    accession_id, efo_trait, efo_id, show_child_trait, mapped_gene,
    extended_geneset, sort, direction, page, size. `p_upper` merely gets
    echoed back inside the HAL _links hrefs -- confirmed live that
    ...&sort=p_value&direction=asc&p_upper=1e-300 still returns all 68
    associations for EFO_0009184. So the threshold stays client-side, and the
    fix is (i) fetch the page most-significant-first so the threshold can
    actually pass rows, (ii) attribute an empty result to the filter rather
    than to the trait, and (iii) disclose that pagination totals are
    pre-filter.

Issue 2 -- a trait name was silently resolved to a different phenotype.
    disease_trait="cardiorespiratory fitness" resolves to EFO_0009184
    ("heart rate response to exercise"), not EFO_0004887 ("maximal oxygen
    uptake measurement"). The resolution is unchanged (re-tuning the matcher
    is out of scope); it is now disclosed: the resolved label and the
    original query string travel back with the id.

Offline only: every HTTP call is patched.
"""

from unittest.mock import patch

import pytest

from tooluniverse.gwas_tool import (
    GWASAssociationSearch,
    GWASAssociationsForTrait,
)

pytestmark = pytest.mark.unit

# Query parameters GET /v2/associations actually declares in the v2 OpenAPI doc.
_SPEC_PARAMS = {
    "pubmed_id",
    "rs_id",
    "full_pvalue_set",
    "accession_id",
    "efo_trait",
    "efo_id",
    "show_child_trait",
    "mapped_gene",
    "extended_geneset",
    "sort",
    "direction",
    "page",
    "size",
}


def _assoc(p_value):
    return {"association_id": int(-1 / p_value) if p_value else 0, "p_value": p_value}


def _run(arguments, associations, page=None):
    """Run gwas_search_associations offline; return (result, captured params)."""
    captured = {}

    def fake_request(endpoint, params=None):
        captured["endpoint"] = endpoint
        captured["params"] = params or {}
        return {
            "_embedded": {"associations": list(associations)},
            "page": page
            if page is not None
            else {"size": 10, "totalElements": 23608, "totalPages": 2361, "number": 0},
        }

    tool = GWASAssociationSearch({"name": "gwas_search_associations"})
    with patch.object(GWASAssociationSearch, "_make_request", side_effect=fake_request):
        result = tool.run(arguments)
    return result, captured["params"]


# --------------------------------------------------------------------------
# (a) the request carries the ordering that makes the threshold real, and
#     nothing the API does not understand
# --------------------------------------------------------------------------


def test_pvalue_filtered_request_is_fetched_most_significant_first():
    """direction=desc + p_value used to guarantee an empty page.

    The threshold cannot be pushed upstream (the v2 spec has no p-value
    parameter), so the request must instead be ordered p_value-ascending --
    otherwise the client-side filter is applied to exactly the rows that
    cannot pass it.
    """
    _, params = _run(
        {
            "efo_id": "EFO_0004340",
            "p_value": 5e-08,
            "sort": "p_value",
            "direction": "desc",
            "size": 10,
        },
        [_assoc(1e-300), _assoc(1e-100), _assoc(5e-09), _assoc(1e-03)],
    )
    assert params["sort"] == "p_value"
    assert params["direction"] == "asc", (
        "a p-value threshold must be evaluated against the most-significant "
        "end of the result set"
    )


def test_request_sends_only_parameters_the_v2_api_declares():
    """No made-up threshold parameter is smuggled upstream.

    `p_upper` and friends are silently ignored by GWAS Catalog (they are only
    echoed into _links), so sending one would fake a server-side filter.
    """
    _, params = _run(
        {"efo_id": "EFO_0004340", "p_value": 5e-08, "size": 10},
        [_assoc(1e-300)],
    )
    assert set(params) <= _SPEC_PARAMS, (
        f"undeclared params sent: {set(params) - _SPEC_PARAMS}"
    )
    for bogus in ("p_upper", "p_value", "p_value_threshold", "pvalue_upper"):
        assert bogus not in params


def test_desc_request_still_returns_the_significant_rows():
    """The BMI repro: data must no longer be empty."""
    result, _ = _run(
        {
            "efo_id": "EFO_0004340",
            "p_value": 5e-08,
            "sort": "p_value",
            "direction": "desc",
            "size": 10,
        },
        [_assoc(1e-300), _assoc(1e-100), _assoc(5e-09), _assoc(1e-03)],
    )
    assert [a["p_value"] for a in result["data"]] == [5e-09, 1e-100, 1e-300]
    assert "note" not in result
    assert result["metadata"]["sort_override"]["fetched_direction"] == "asc"
    assert result["metadata"]["sort_override"]["requested_direction"] == "desc"


# --------------------------------------------------------------------------
# (b) an empty page caused by the filter blames the filter, not the trait
# --------------------------------------------------------------------------


def test_filter_emptied_page_note_names_the_filter():
    result, _ = _run(
        {"efo_id": "EFO_0004340", "p_value": 1e-320, "size": 10},
        [_assoc(1e-300), _assoc(1e-100), _assoc(5e-09)],
        page={"size": 10, "totalElements": 23608, "totalPages": 2361, "number": 0},
    )
    assert result["data"] == []
    note = result["note"]
    assert "filter" in note.lower()
    assert "1e-320" in note
    assert "23608" in note, "the note should show how much data the trait really has"
    assert "removed" in note.lower()


def test_filter_emptied_page_note_does_not_blame_the_efo_term():
    result, _ = _run(
        {"efo_id": "EFO_0004340", "p_value": 1e-320, "size": 10},
        [_assoc(1e-300), _assoc(1e-100)],
    )
    note = result["note"]
    assert "synonym" not in note.lower()
    assert "different" not in note.lower() or "EFO/MONDO term" not in note
    assert "GWAS_search_associations_by_gene" not in note
    assert "gwas_get_snps_for_gene" not in note
    assert "No associations found for EFO ID" not in note


# --------------------------------------------------------------------------
# (c) a genuinely empty UNFILTERED result set keeps the original advice
# --------------------------------------------------------------------------


def test_genuinely_empty_result_still_gets_trait_advice():
    result, _ = _run(
        {"efo_id": "EFO_0004340", "size": 10},
        [],
        page={"size": 10, "totalElements": 0, "totalPages": 0, "number": 0},
    )
    note = result["note"]
    assert "No associations found for EFO ID 'EFO_0004340'" in note
    assert "synonym" in note
    assert "GWAS_search_associations_by_gene" in note
    assert "gwas_get_snps_for_gene" in note


def test_genuinely_empty_result_with_threshold_also_gets_trait_advice():
    """A threshold that removed nothing must not hijack the trait advice."""
    result, _ = _run(
        {"efo_id": "EFO_0004340", "p_value": 5e-08, "size": 10},
        [],
        page={"size": 10, "totalElements": 0, "totalPages": 0, "number": 0},
    )
    assert "No associations found for EFO ID 'EFO_0004340'" in result["note"]


# --------------------------------------------------------------------------
# (d) pagination totals are disclosed as pre-filter
# --------------------------------------------------------------------------


def test_pagination_totals_are_disclosed_as_prefilter():
    """EFO_0009184: 63 of 68 rows pass 5e-08, but totalElements stays 68."""
    associations = [_assoc(1e-30)] * 63 + [_assoc(1e-03)] * 5
    result, _ = _run(
        {"efo_id": "EFO_0009184", "p_value": 5e-08, "size": 100},
        associations,
        page={"size": 100, "totalElements": 68, "totalPages": 1, "number": 0},
    )
    metadata = result["metadata"]
    # totalElements keeps its established (unfiltered) meaning ...
    assert metadata["pagination"]["totalElements"] == 68
    # ... and the pre-filter nature is stated explicitly.
    assert metadata["pagination_totals_are_prefilter"] is True
    assert metadata["p_value_filter_scope"].startswith("client-side")
    assert "client-side" in metadata["p_value_filter_note"].lower()
    assert "UNFILTERED" in metadata["filtered_total_note"]
    # ... alongside a separately named, correct filtered denominator.
    assert metadata["filtered_total"] == 63
    assert metadata["filtered_total_is_exact"] is True
    assert metadata["filtered_count"] == 63
    assert len(result["data"]) == 63


def test_filtered_total_is_not_faked_when_a_page_cannot_determine_it():
    """Every fetched row passed, so the true filtered total is unknown."""
    result, _ = _run(
        {"efo_id": "EFO_0004340", "p_value": 5e-08, "size": 3},
        [_assoc(1e-300), _assoc(1e-100), _assoc(1e-30)],
        page={"size": 3, "totalElements": 23608, "totalPages": 7870, "number": 0},
    )
    metadata = result["metadata"]
    assert metadata["filtered_total"] is None
    assert metadata["filtered_total_is_exact"] is False
    assert metadata["filtered_total_at_least"] == 3
    assert metadata["pagination_totals_are_prefilter"] is True


# --------------------------------------------------------------------------
# (e) a resolved trait discloses the EFO id, its label and the original query
# --------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


def _fake_gwas_get(url, params=None, timeout=None, **kwargs):
    """Reproduces the live resolver traffic for 'cardiorespiratory fitness'."""
    if "efoTraits/search/findByEfoTrait" in url:
        return _FakeResponse({"_embedded": {"efoTraits": []}})
    if url.endswith("/v2/studies"):
        return _FakeResponse(
            {
                "_embedded": {
                    "studies": [
                        {
                            "accession_id": "GCST90310239",
                            "disease_trait": "Cardiorespiratory fitness",
                            "efo_traits": [
                                {
                                    "efo_id": "EFO_0009184",
                                    "efo_trait": "heart rate response to exercise",
                                }
                            ],
                        }
                    ]
                }
            }
        )
    raise AssertionError(f"unexpected HTTP call in offline test: {url}")


def _run_trait_tool(arguments, associations):
    def fake_request(endpoint, params=None):
        return {
            "_embedded": {"associations": list(associations)},
            "page": {"size": 3, "totalElements": 68, "totalPages": 23, "number": 0},
        }

    tool = GWASAssociationsForTrait({"name": "gwas_get_associations_for_trait"})
    with patch("tooluniverse.gwas_tool.requests.get", side_effect=_fake_gwas_get):
        with patch.object(
            GWASAssociationsForTrait, "_make_request", side_effect=fake_request
        ):
            return tool.run(arguments)


def test_resolved_trait_returns_id_label_and_original_query():
    result = _run_trait_tool(
        {"disease_trait": "cardiorespiratory fitness", "size": 3},
        [_assoc(3e-30)],
    )
    assert result["resolved_efo_id"] == "EFO_0009184"
    assert result["resolved_efo_label"] == "heart rate response to exercise"
    assert result["query_trait"] == "cardiorespiratory fitness"
    assert "GCST90310239" in result["trait_resolution_source"]


def test_inexact_trait_resolution_is_flagged():
    result = _run_trait_tool(
        {"disease_trait": "cardiorespiratory fitness", "size": 3},
        [_assoc(3e-30)],
    )
    note = result["trait_resolution_note"]
    assert "cardiorespiratory fitness" in note
    assert "heart rate response to exercise" in note
    assert "EFO_0009184" in note
    assert "not an exact match" in note.lower() or "SUBSTITUTION" in note


def test_exact_trait_resolution_is_not_flagged_as_a_substitution():
    def exact_get(url, params=None, timeout=None, **kwargs):
        if "efoTraits/search/findByEfoTrait" in url:
            return _FakeResponse(
                {
                    "_embedded": {
                        "efoTraits": [{"trait": "asthma", "shortForm": "MONDO_0004979"}]
                    }
                }
            )
        raise AssertionError(f"unexpected HTTP call: {url}")

    def fake_request(endpoint, params=None):
        return {
            "_embedded": {"associations": [_assoc(7e-288)]},
            "page": {"size": 3, "totalElements": 3219, "totalPages": 1073, "number": 0},
        }

    tool = GWASAssociationsForTrait({"name": "gwas_get_associations_for_trait"})
    with patch("tooluniverse.gwas_tool.requests.get", side_effect=exact_get):
        with patch.object(
            GWASAssociationsForTrait, "_make_request", side_effect=fake_request
        ):
            result = tool.run({"disease_trait": "asthma", "size": 3})

    assert result["resolved_efo_id"] == "MONDO_0004979"
    assert result["resolved_efo_label"] == "asthma"
    assert result["query_trait"] == "asthma"
    assert "trait_resolution_note" not in result


def test_search_tool_also_discloses_the_resolved_label():
    def fake_request(endpoint, params=None):
        return {
            "_embedded": {"associations": [_assoc(3e-30)]},
            "page": {"size": 3, "totalElements": 68, "totalPages": 23, "number": 0},
        }

    tool = GWASAssociationSearch({"name": "gwas_search_associations"})
    with patch("tooluniverse.gwas_tool.requests.get", side_effect=_fake_gwas_get):
        with patch.object(
            GWASAssociationSearch, "_make_request", side_effect=fake_request
        ):
            result = tool.run({"disease_trait": "cardiorespiratory fitness", "size": 3})

    assert result["resolved_efo_id"] == "EFO_0009184"
    assert result["resolved_efo_label"] == "heart rate response to exercise"
    assert result["query_trait"] == "cardiorespiratory fitness"
    assert "trait_resolution_note" in result
