"""Unit test: ClinVar_search_variants must say when the `condition` it accepted
did not act as a disease filter, and must blame the input that actually emptied
a result.

Two symptoms of the same gap, both reproduced live before the fix:

  * `{"gene":"RPE65","condition":"Leber congenital amaurosis"}` -> 996 records,
    query_translation '... AND "Leber congenital amaurosis"[dis]'.
    `{"gene":"RPE65","condition":"Lebers congenital amaurosis"}` (one letter
    different) -> 1 record, query_translation '... AND "Lebers congenital
    amaurosis"[All Fields]'. Both plain successes, no warning: the second count
    is a free-text substring artifact presented exactly like a disease-filtered
    count. (Confirmed live via raw E-utils that '"Lebers congenital
    amaurosis"[dis]' returns 0, i.e. the [All Fields] form comes from this
    module's own untagged retry -- and an Entrez rewrite of the tag would look
    the same in the response, so both are detected from `querytranslation`,
    with no extra request.)

  * a zero-result response used to blame the gene symbol unconditionally, so a
    condition name that ClinVar's disease index does not carry sent the caller
    off re-verifying the one input that was correct.

Pins: the disclosure is a top-level key, it fires only when there is evidence
for it, and the zero-result hint names the condition when the condition is what
failed while the original gene-symbol guidance still fires when the gene is.
"""

from unittest.mock import patch

import pytest

from tooluniverse.clinvar_tool import ClinVarSearchVariants, _field_tags_for_term

pytestmark = pytest.mark.unit


def _tool():
    return ClinVarSearchVariants({"name": "ClinVar_search_variants"})


def _esearch(count, query_translation="", ids=None):
    return {
        "status": "success",
        "data": {
            "esearchresult": {
                "count": str(count),
                "idlist": ids or [],
                "querytranslation": query_translation,
            }
        },
    }


def _run(arguments, responder):
    """Run the tool with every HTTP call answered by `responder(params)`."""
    tool = _tool()

    def fake_request(_endpoint, params=None, **_kwargs):
        return responder(params or {})

    with patch.object(
        ClinVarSearchVariants, "_make_request", side_effect=fake_request
    ) as mock_request:
        result = tool.run(arguments)
    return result, mock_request


# --- (a) a condition that really is applied as a disease filter -------------


def test_indexed_condition_is_reported_as_disease_filtered():
    """[dis] survived in the translation -> the count means what it looks
    like, and no warning is invented."""
    translation = 'RPE65[gene] AND "Leber congenital amaurosis"[dis]'
    result, _ = _run(
        {"gene": "RPE65", "condition": "Leber congenital amaurosis", "max_results": 1},
        lambda params: _esearch(996, translation),
    )

    data = result["data"]
    assert result["status"] == "success"
    assert data["total_count"] == 996
    assert data["condition_filter_applied"] is True
    assert "condition_filter_warning" not in data
    assert "condition_search_field" not in data


def test_no_disclosure_is_invented_without_a_translation():
    """No querytranslation echoed back -> no evidence either way, so the tool
    must not cry wolf (this is the shape older mocked tests use)."""
    result, _ = _run(
        {"gene": "FBN1", "condition": "Marfan syndrome"},
        lambda params: _esearch(100, ""),
    )
    data = result["data"]
    assert "condition_filter_warning" not in data
    assert "condition_filter_applied" not in data


# --- (b) a condition that ends up searched as free text --------------------


def _untagged_retry_responder(dis_translation, freetext_translation):
    """First (disease-restricted) search finds nothing; the module's untagged
    retry finds one free-text match -- the live 'Lebers congenital amaurosis'
    sequence."""

    def responder(params):
        term = params.get("term", "")
        if "[dis]" in term:
            return _esearch(0, dis_translation)
        return _esearch(1, freetext_translation, ids=["98846"])

    return responder


def test_free_text_fallback_count_is_disclosed_as_not_disease_filtered():
    result, _ = _run(
        {"gene": "RPE65", "condition": "Lebers congenital amaurosis", "max_results": 1},
        _untagged_retry_responder(
            'RPE65[gene] AND "Lebers congenital amaurosis"[dis]',
            'RPE65[gene] AND "Lebers congenital amaurosis"[All Fields]',
        ),
    )

    data = result["data"]
    assert data["total_count"] == 1
    # Top-level, not buried in a nested note.
    assert data["condition_filter_applied"] is False
    assert data["condition_search_field"] == "All Fields"
    warning = data["condition_filter_warning"]
    assert "NOT disease-filtered" in warning
    assert "Lebers congenital amaurosis" in warning
    assert "All Fields" in warning
    # ...and it says what to do about it.
    assert "MedGen_search_conditions" in warning


def test_entrez_rewriting_the_tag_is_disclosed_too():
    """Same disclosure when the [dis] tag simply does not come back, without
    this module having retried anything."""
    result, mock_request = _run(
        {"gene": "RPE65", "condition": "Lebers congenital amaurosis"},
        lambda params: _esearch(
            1, 'RPE65[gene] AND "Lebers congenital amaurosis"[All Fields]'
        ),
    )

    data = result["data"]
    assert data["condition_filter_applied"] is False
    assert data["condition_search_field"] == "All Fields"
    assert "NOT disease-filtered" in data["condition_filter_warning"]
    # Detected from the translation already in hand -- one search request.
    assert mock_request.call_count == 1


def test_single_word_condition_degradation_is_detected():
    """An unquoted single-word term (a locus name like RP20) is matched by the
    same translation parsing."""
    result, _ = _run(
        {"gene": "RPE65", "condition": "RP20"},
        _untagged_retry_responder(
            "RPE65[gene] AND RP20[dis]", "RPE65[gene] AND RP20[All Fields]"
        ),
    )
    assert result["data"]["condition_filter_applied"] is False
    assert "RP20" in result["data"]["condition_filter_warning"]


def test_field_tag_parsing_is_not_confused_by_neighbouring_terms():
    translation = (
        'RPE65[gene] AND "Lebers congenital amaurosis"[All Fields] AND '
        '("clinsig pathogenic"[Filter] OR clinsig_pathogenic[prop])'
    )
    assert _field_tags_for_term(translation, '"Lebers congenital amaurosis"') == [
        "All Fields"
    ]
    assert _field_tags_for_term(translation, "RPE65") == ["gene"]
    assert _field_tags_for_term(translation, "not in the query") == []


# --- (c) an empty result caused by the condition ---------------------------


def test_zero_results_with_an_untranslated_condition_names_the_condition():
    """The condition was not applied as a disease filter and nothing matched:
    the hint must point at the condition, not send the caller off to
    re-verify a valid gene symbol."""

    def responder(params):
        if params.get("retmax") == 0 and params.get("term") == "RPE65[gene]":
            return _esearch(1183, "RPE65[gene]")
        return _esearch(0, 'RPE65[gene] AND "Lebers congenital amaurosis"[All Fields]')

    result, _ = _run(
        {"gene": "RPE65", "condition": "Lebers congenital amaurosis"}, responder
    )

    hint = result["data"]["zero_result_hint"]
    assert "Lebers congenital amaurosis" in hint
    assert "not applied as a disease filter" in hint
    assert "MedGen_search_conditions" in hint
    # The valid gene symbol is exonerated, not blamed.
    assert "HGNC" not in hint
    assert "outdated/misspelled" not in hint
    assert "is not the problem" in hint
    assert result["data"]["gene_only_match_count"] == 1183


def test_zero_results_with_a_condition_absent_from_the_disease_index():
    """The [dis] tag survived, but the condition name matches nothing anywhere
    in ClinVar -- still the condition's doing, not the gene's."""

    def responder(params):
        term = params.get("term", "")
        if params.get("retmax") == 0 and term == "RPE65[gene]":
            return _esearch(1183, term)
        return _esearch(0, 'RPE65[gene] AND "Made Up Syndrome"[dis]')

    result, _ = _run({"gene": "RPE65", "condition": "Made Up Syndrome"}, responder)

    data = result["data"]
    assert data["condition_only_match_count"] == 0
    hint = data["zero_result_hint"]
    assert "'Made Up Syndrome' matches no ClinVar records at all" in hint
    assert "HGNC" not in hint
    assert "1183" in hint


def test_zero_results_with_a_real_condition_says_gene_and_condition_dont_meet():
    """Both inputs are individually fine -- 'no data' rather than 'bad query'."""

    def responder(params):
        term = params.get("term", "")
        if params.get("retmax") == 0 and term == "RPE65[gene]":
            return _esearch(1183, term)
        if params.get("retmax") == 0 and term == '"breast cancer"[dis]':
            return _esearch(240000, term)
        return _esearch(
            0,
            'RPE65[gene] AND "breast cancer"[dis] AND '
            '("clinsig pathogenic"[Filter] OR clinsig_pathogenic[prop])',
        )

    result, _ = _run(
        {
            "gene": "RPE65",
            "condition": "breast cancer",
            "clinical_significance": "Pathogenic",
        },
        responder,
    )

    data = result["data"]
    assert data["condition_filter_applied"] is True
    assert data["condition_only_match_count"] == 240000
    hint = data["zero_result_hint"]
    assert "'RPE65' is fine" in hint
    assert "recognized ClinVar disease term" in hint
    assert "no record in common" in hint
    assert "HGNC" not in hint


def test_condition_only_search_with_no_gene_still_gets_a_hint():
    def responder(params):
        term = params.get("term", "")
        if params.get("retmax") == 0 and term == '"breast cancer"[dis]':
            return _esearch(240000, term)
        return _esearch(0, '"breast cancer"[dis] AND 12345[uid]')

    result, _ = _run({"condition": "breast cancer", "variant_id": "12345"}, responder)

    hint = result["data"]["zero_result_hint"]
    assert "breast cancer" in hint
    assert "variant_id" in hint


# --- (d) an empty result that really is the gene's fault -------------------


def test_zero_results_without_a_condition_keeps_the_gene_symbol_guidance():
    result, mock_request = _run({"gene": "NOTAGENE123"}, lambda params: _esearch(0))

    hint = result["data"]["zero_result_hint"]
    assert "No ClinVar records matched gene 'NOTAGENE123'" in hint
    assert "HGNC" in hint
    assert "HGNC_search_genes" in hint
    # No condition was supplied, so no condition probe is issued.
    assert all(
        "[dis]" not in (call[0][1] or {}).get("term", "")
        for call in mock_request.call_args_list
    )


def test_unknown_gene_with_a_valid_condition_still_reaches_the_gene_guidance():
    """The condition is a real disease term and the gene matches nothing even
    on its own -> the original symbol guidance is what the caller needs."""

    def responder(params):
        term = params.get("term", "")
        if params.get("retmax") == 0 and term == '"breast cancer"[dis]':
            return _esearch(240000, term)
        if params.get("retmax") == 0:
            return _esearch(0, term)
        if params.get("db") == "gene":
            return {"status": "success", "data": {"esearchresult": {"idlist": []}}}
        return _esearch(0, 'NOTAGENE123[gene] AND "breast cancer"[dis]')

    result, _ = _run({"gene": "NOTAGENE123", "condition": "breast cancer"}, responder)

    hint = result["data"]["zero_result_hint"]
    assert "No ClinVar records matched gene 'NOTAGENE123'" in hint
    assert "HGNC" in hint
