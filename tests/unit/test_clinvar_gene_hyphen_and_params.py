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

Fix-R5D-1/R8C-1: an unrecognized parameter (e.g. "variant_nam", a typo of a
real param) was silently dropped. When it was the only param supplied, this
produced a generic "at least one search parameter is required" error; when
other valid params were also supplied, the query ran but silently ignored
the unrecognized one with no indication the filter had zero effect. (Note:
"variant_name" itself was originally this fix's own illustrative example of
a parameter that "doesn't exist" -- Fix-R78B-1 later added it as a real,
working parameter; see test_clinvar_variant_name_search.py.)
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
    must not error or loop -- just report 0. A third call now also happens
    (Fix-R62A-1's deprecated-symbol gene-database lookup), which itself
    finds nothing (empty idlist) so no further retry is attempted."""
    tool = _tool()
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        side_effect=[
            _esearch_result(0),
            _esearch_result(0),
            {"status": "success", "data": {"esearchresult": {"idlist": []}}},
        ],
    ) as mock_request:
        result = tool.run({"gene": "NOT-A-REAL-GENE"})

    assert mock_request.call_count == 3
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
    result = tool.run({"varient_name": "35delG"})

    assert result["status"] == "error"
    assert "varient_name" in result["error"]
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
        result = tool.run({"gene": "GJB2", "varient_name": "35delG"})

    assert result["status"] == "success"
    assert result["data"]["ignored_parameters"] == ["varient_name"]
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


def _gene_db_result(ids):
    return {"status": "success", "data": {"esearchresult": {"idlist": ids}}}


def _gene_summary_result(gene_id, current_symbol):
    return {
        "status": "success",
        "data": {"result": {gene_id: {"name": current_symbol}}},
    }


def test_deprecated_gene_symbol_resolves_via_ncbi_gene_database():
    """Fix-R62A-1: "GBA" (glucocerebrosidase, Gaucher disease) was renamed
    to "GBA1" in 2023 -- ClinVar's [gene] index fully absorbed the rename
    with no backward-compat alias, unlike the hyphen case, so no string
    transform recovers it. Confirmed live: "GBA[gene]" -> 0 hits (not even
    a hyphen to strip), "GBA1[gene]" -> 786 hits. Resolve via NCBI's own
    gene database (which tracks "GBA" as an alias of gene ID 2629, current
    symbol "GBA1") and retry."""
    tool = _tool()
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        side_effect=[
            _esearch_result(0),  # GBA[gene] -- no hyphen, so only 1 attempt
            _gene_db_result(["2629"]),  # db=gene esearch for "GBA"
            _gene_summary_result("2629", "GBA1"),  # db=gene esummary
            _esearch_result(786, query_translation="GBA1[gene]"),  # retry
        ],
    ) as mock_request:
        result = tool.run({"gene": "GBA"})

    assert mock_request.call_count == 4
    assert mock_request.call_args_list[-1][0][1]["term"] == "GBA1[gene]"
    assert result["data"]["total_count"] == 786
    # search_params still echoes back what the caller actually asked for.
    assert result["data"]["search_params"]["gene"] == "GBA"


def test_gene_database_resolving_to_the_same_symbol_does_not_retry():
    """If NCBI's gene database resolves the queried symbol right back to
    itself (already current, genuinely 0 pathogenic hits for some other
    reason -- e.g. an overly narrow significance filter), no pointless
    retry should be attempted."""
    tool = _tool()
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        side_effect=[
            _esearch_result(0),
            _gene_db_result(["7157"]),
            _gene_summary_result("7157", "TP53"),
        ],
    ) as mock_request:
        result = tool.run({"gene": "TP53"})

    assert mock_request.call_count == 3
    assert result["data"]["total_count"] == 0


def test_gene_database_lookup_failure_does_not_crash_or_error():
    """The gene-database fallback is best-effort -- a network error there
    must not surface as a tool failure, just leave the result at 0."""
    tool = _tool()
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        side_effect=[
            _esearch_result(0),
            {"status": "error", "error": "Could not find a suitable TLS CA certificate bundle"},
        ],
    ) as mock_request:
        result = tool.run({"gene": "GBA"})

    assert mock_request.call_count == 2
    assert result["status"] == "success"
    assert result["data"]["total_count"] == 0
