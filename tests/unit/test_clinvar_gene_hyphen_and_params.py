"""Regression guard for ClinVar_search_variants gene-hyphen handling and
unrecognized-parameter fixes:

Fix-R8B-1/Fix-R49A-1: HGNC gene symbols usually don't contain hyphens, but
informal usage still writes some hyphenated (e.g. "BRCA-2" for "BRCA2").
ClinVar's [gene] index only matches the canonical unhyphenated form for
those, so a hyphenated query silently returned 0 results. R8B-1 originally
"fixed" this by unconditionally stripping every hyphen -- but that broke
every gene whose CURRENT official HGNC symbol genuinely contains one
(confirmed live: the entire HLA family, the NKX homeobox family, and MT-
mitochondrial genes all need the hyphen PRESERVED, e.g. "HLA-B[gene]" ->
130 hits but "HLAB[gene]" -> 0). Fix-R49A-1 queries with the hyphen
preserved first, falling back to the stripped form only if that returns
zero results, so both cases resolve correctly without a hardcoded gene list.

Fix-R5D-1/R8C-1: an unrecognized parameter (e.g. "variant_name", which
doesn't exist -- only "variant_id" does) was silently dropped. When it was
the only param supplied, this produced a generic "at least one search
parameter is required" error; when other valid params were also supplied,
the query ran but silently ignored the unrecognized one with no
indication the filter had zero effect.
"""

from unittest.mock import patch

import pytest

from tooluniverse.clinvar_tool import ClinVarSearchVariants

pytestmark = pytest.mark.unit


def _tool():
    return ClinVarSearchVariants({"name": "ClinVar_search_variants"})


def _esearch_result(count, ids=None, query_translation=""):
    return {
        "status": "success",
        "data": {
            "esearchresult": {
                "idlist": ids or [],
                "count": str(count),
                "querytranslation": query_translation,
            }
        },
    }


def test_hyphenated_official_symbol_is_queried_with_hyphen_preserved():
    """HLA-B, NKX2-5, MT-ND1 etc. -- the hyphen is part of the real symbol,
    so the first (and in this case only, since it succeeds) request must
    keep it. ids left empty so no follow-up esummary.fcgi call is made --
    this test only exercises the query-building/retry logic."""
    tool = _tool()
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        return_value=_esearch_result(130, query_translation="HLA-B[gene]"),
    ) as mock_request:
        result = tool.run({"gene": "HLA-B"})

    assert mock_request.call_count == 1
    assert mock_request.call_args[0][1]["term"] == "HLA-B[gene]"
    assert result["data"]["total_count"] == 130


def test_informally_hyphenated_symbol_falls_back_to_stripped_form():
    """BRCA-2 -- the hyphen-preserved attempt returns 0, so a second
    request with the hyphen stripped must be made and its result used."""
    tool = _tool()
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        side_effect=[
            _esearch_result(0),
            _esearch_result(21879, query_translation="BRCA2[gene]"),
        ],
    ) as mock_request:
        result = tool.run({"gene": "BRCA-2"})

    assert mock_request.call_count == 2
    assert mock_request.call_args_list[0][0][1]["term"] == "BRCA-2[gene]"
    assert mock_request.call_args_list[1][0][1]["term"] == "BRCA2[gene]"
    assert result["data"]["total_count"] == 21879


def test_hyphen_fallback_preserves_other_query_parts():
    """gene + condition together -- the fallback retry must keep the
    condition term, not just the gene term."""
    tool = _tool()
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        side_effect=[_esearch_result(0), _esearch_result(203)],
    ) as mock_request:
        tool.run({"gene": "BRCA-2", "condition": "breast cancer"})

    second_term = mock_request.call_args_list[1][0][1]["term"]
    assert second_term == 'BRCA2[gene] AND "breast cancer"[dis]'


def test_hyphenated_gene_with_no_real_match_stays_zero_after_fallback():
    """Both the hyphenated and stripped attempts genuinely finding nothing
    must not error or loop -- just report 0."""
    tool = _tool()
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        side_effect=[_esearch_result(0), _esearch_result(0)],
    ) as mock_request:
        result = tool.run({"gene": "NOT-A-REAL-GENE"})

    assert mock_request.call_count == 2
    assert result["data"]["total_count"] == 0


def test_plain_gene_symbol_unaffected():
    """No hyphen in the gene arg -- exactly one request, no fallback
    attempt regardless of what count comes back."""
    tool = _tool()
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        return_value=_esearch_result(1624),
    ) as mock_request:
        tool.run({"gene": "BRCA2"})

    assert mock_request.call_count == 1
    assert "BRCA2[gene]" in mock_request.call_args[0][1]["term"]


def test_unrecognized_param_alone_names_itself_in_error():
    tool = _tool()
    result = tool.run({"variant_name": "35delG"})

    assert result["status"] == "error"
    assert "variant_name" in result["error"]
    assert "Unrecognized parameter" in result["error"]


def test_unrecognized_param_alongside_valid_param_is_noted_not_silently_dropped():
    tool = _tool()
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        side_effect=[
            {
                "status": "success",
                "data": {
                    "esearchresult": {
                        "idlist": [],
                        "count": "739",
                        "querytranslation": "GJB2[gene]",
                    }
                },
            },
        ],
    ):
        result = tool.run({"gene": "GJB2", "variant_name": "35delG"})

    assert result["status"] == "success"
    assert result["data"]["ignored_parameters"] == ["variant_name"]
    assert result["data"]["total_count"] == 739


def test_all_valid_params_have_no_ignored_parameters_key():
    tool = _tool()
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        return_value={
            "status": "success",
            "data": {"esearchresult": {"idlist": [], "count": "1", "querytranslation": ""}},
        },
    ):
        result = tool.run({"gene": "BRCA2"})

    assert result["status"] == "success"
    assert "ignored_parameters" not in result["data"]
