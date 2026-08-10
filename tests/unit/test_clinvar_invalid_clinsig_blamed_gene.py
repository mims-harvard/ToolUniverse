"""Unit test: an unrecognized clinical_significance is rejected at the input,
and the zero-result hint stops blaming the gene for a filter's empty result.

Regression: `{"gene": "TP53", "clinical_significance": "Banana"}` pasted the
bogus class straight into the Entrez term, matched nothing, and returned
`status: success` with total_count 0 plus a hint telling the caller to
re-verify the gene symbol -- TP53, which matches thousands of records on its
own. The only trace of the real culprit was buried in query_translation.

Pins three things:
  * an unrecognized value (via either parameter spelling) is an ERROR that
    names the parameter and lists the accepted classes, and never reaches the
    network;
  * every accepted class still builds its verified [Filter]/[prop] clause;
  * the genuine gene-symbol hint still fires unchanged for an unknown gene.
"""

from unittest.mock import patch

import pytest

from tooluniverse.clinvar_tool import (
    _CLINSIG_ACCEPTED,
    ClinVarSearchByRegion,
    ClinVarSearchVariants,
)

pytestmark = pytest.mark.unit


def _tool():
    return ClinVarSearchVariants({"name": "ClinVar_search_variants"})


def _run(arguments, count="0"):
    """Run the tool with the network stubbed; returns (result, mock)."""
    tool = _tool()
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        return_value={
            "status": "success",
            "data": {"esearchresult": {"count": count, "idlist": []}},
        },
    ) as mock_request:
        result = tool.run(arguments)
    return result, mock_request


# --- 1. invalid values are rejected up front -------------------------------


@pytest.mark.parametrize("param", ["clinical_significance", "significance"])
def test_invalid_value_is_an_error_naming_the_parameter(param):
    result, mock_request = _run({"gene": "TP53", param: "Banana"})

    assert result["status"] == "error"
    assert result["parameter"] == param
    # The offending parameter is named; the (valid) gene symbol is not blamed.
    assert param in result["error"]
    assert "banana" in result["error"].lower()
    assert "HGNC" not in result["error"]
    assert "verify the symbol" not in result["error"]
    # The accepted classes are listed so the caller can self-correct.
    for accepted in ("Pathogenic", "Likely benign", "risk factor"):
        assert accepted in result["error"]
    assert "Pathogenic" in result["valid_values"]
    # ...and no query was ever sent.
    mock_request.assert_not_called()


def test_invalid_component_of_a_slash_value_is_rejected():
    result, mock_request = _run(
        {"gene": "TP53", "clinical_significance": "Pathogenic/Bananas"}
    )
    assert result["status"] == "error"
    assert result["invalid_values"] == ["bananas"]
    mock_request.assert_not_called()


def test_invalid_value_never_reports_success_with_zero_results():
    result, _ = _run({"gene": "TP53", "clinical_significance": "probably bad"})
    assert result["status"] != "success"
    assert "data" not in result


# --- 2. every accepted class still builds its verified clause --------------


@pytest.mark.parametrize("value", _CLINSIG_ACCEPTED)
def test_accepted_values_still_query(value):
    result, mock_request = _run({"gene": "BRCA2", "clinical_significance": value})
    assert result["status"] == "success"
    term = mock_request.call_args_list[0][0][1]["term"]
    normalized = value.lower()
    assert f'"clinsig {normalized}"[Filter]' in term
    assert f"clinsig_{normalized.replace(' ', '_')}[prop]" in term


@pytest.mark.parametrize(
    "spelling", ["Pathogenic", "pathogenic", "PATHOGENIC", " Pathogenic "]
)
def test_case_and_whitespace_spellings_accepted(spelling):
    result, _ = _run({"gene": "BRCA2", "clinical_significance": spelling})
    assert result["status"] == "success"


@pytest.mark.parametrize("spelling", ["risk_factor", "risk-factor", "Risk Factor"])
def test_underscore_and_hyphen_spellings_map_to_the_indexed_token(spelling):
    result, mock_request = _run({"gene": "HFE", "clinical_significance": spelling})
    assert result["status"] == "success"
    assert "clinsig_risk_factor[prop]" in mock_request.call_args_list[0][0][1]["term"]


def test_alias_and_canonical_parameter_build_the_same_query():
    _, canonical = _run({"gene": "NLRP7", "clinical_significance": "Pathogenic"})
    _, alias = _run({"gene": "NLRP7", "significance": "Pathogenic"})
    assert (
        canonical.call_args_list[0][0][1]["term"]
        == alias.call_args_list[0][0][1]["term"]
    )


# --- 3. the gene-symbol hint is preserved, but only when it's earned -------


def test_unknown_gene_with_no_filter_still_gets_the_gene_symbol_hint():
    result, _mock_request = _run({"gene": "NOTAGENE123"})

    hint = result["data"]["zero_result_hint"]
    assert "No ClinVar records matched gene 'NOTAGENE123'" in hint
    assert "HGNC" in hint
    assert "HGNC_search_genes" in hint
    # No filters were supplied, so no evidence query is needed to say this.
    assert "gene_only_match_count" not in result["data"]


def test_unknown_gene_with_a_filter_still_blames_the_gene():
    """The bare-gene probe also returns 0 -> the symbol really is the problem."""
    result, _ = _run({"gene": "NOTAGENE123", "clinical_significance": "Pathogenic"})

    hint = result["data"]["zero_result_hint"]
    assert "No ClinVar records matched gene 'NOTAGENE123'" in hint
    assert "HGNC" in hint
    assert result["data"]["gene_only_match_count"] == 0


def _dispatching_run(arguments, probe_response):
    """Run with a stub that answers the bare-gene evidence probe (retmax=0)
    with `probe_response` and everything else with an empty result set."""
    empty = {
        "status": "success",
        "data": {"esearchresult": {"count": "0", "idlist": []}},
    }

    def responder(_endpoint, params=None, **_kwargs):
        params = params or {}
        if params.get("retmax") == 0:
            return probe_response
        return empty

    tool = _tool()
    with patch.object(
        ClinVarSearchVariants, "_make_request", side_effect=responder
    ) as mock_request:
        result = tool.run(arguments)
    return result, mock_request


def test_valid_gene_with_a_filter_blames_the_filter_not_the_gene():
    """The bare-gene probe returns hits -> the filter emptied the result."""
    result, mock_request = _dispatching_run(
        {"gene": "NLRP7", "clinical_significance": "Established risk allele"},
        {
            "status": "success",
            "data": {"esearchresult": {"count": "434", "idlist": []}},
        },
    )

    hint = result["data"]["zero_result_hint"]
    assert result["data"]["gene_only_match_count"] == 434
    assert "'NLRP7' is fine" in hint
    assert "clinical_significance" in hint
    # It must NOT tell the caller to go re-verify a symbol that matched 434.
    assert "HGNC" not in hint
    assert "outdated/misspelled" not in hint
    # The probe is count-only and reuses the gene term.
    probes = [
        call[0][1]
        for call in mock_request.call_args_list
        if (call[0][1] or {}).get("retmax") == 0
    ]
    assert [p["term"] for p in probes] == ["NLRP7[gene]"]


def test_hint_is_hedged_when_the_evidence_probe_fails():
    result, _ = _dispatching_run(
        {"gene": "NLRP7", "clinical_significance": "Pathogenic"},
        {"status": "error", "error": "boom"},
    )

    hint = result["data"]["zero_result_hint"]
    assert "could not be checked" in hint
    assert "HGNC" not in hint


# --- 4. the sibling region search shares the validation --------------------


def test_region_search_rejects_an_invalid_significance():
    tool = ClinVarSearchByRegion({"name": "ClinVar_search_by_region"})
    result = tool.run(
        {"region": "chr7:155593770-155593780", "clinical_significance": "Banana"}
    )
    assert result["status"] == "error"
    assert result["parameter"] == "clinical_significance"
    assert "banana" in result["error"].lower()
