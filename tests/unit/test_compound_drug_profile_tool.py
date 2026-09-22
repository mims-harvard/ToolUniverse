"""Unit tests for gather_drug_profile.

These cover the parts that must not depend on a live upstream: the resolution
step, where a relevance-ranked search can silently substitute a different drug,
the two cross-checks, and the type normalization.
"""

from tooluniverse.compound_drug_profile_tool import (
    SECTIONS,
    CompoundDrugProfileTool,
    _as_number,
    _is_not_found,
    _records_needed,
)


def _tool():
    return CompoundDrugProfileTool(
        {
            "name": "gather_drug_profile",
            "type": "CompoundDrugProfileTool",
            "parameter": {"type": "object", "properties": {}},
        }
    )


def _hits(*pairs):
    return {
        "status": "success",
        "data": {"search": {"hits": [{"id": i, "name": n} for i, n in pairs]}},
    }


def test_exact_name_wins_over_relevance_rank():
    """OpenTargets' drug search is ranked, not exact.

    'aspirin' really does return [ASPIRIN, IMATINIB, ...]. Taking hits[0] works
    here by luck; taking the first *matching* name is what makes it correct when
    the wanted drug is not ranked first.
    """
    tool = _tool()
    responses = {
        "OpenTargets_get_drug_chembId_by_generic_name": _hits(
            ("CHEMBL941", "IMATINIB"), ("CHEMBL25", "ASPIRIN")
        ),
        "PubChem_get_CID_by_compound_name": {"status": "success", "data": {}},
        "RxNorm_find_rxcui": {"status": "success", "data": {}},
    }
    resolved = tool._resolve(
        lambda _s, name, _a, **_kw: responses[name], lambda *a: None, "aspirin"
    )
    assert resolved["chembl_id"] == "CHEMBL25"
    assert resolved["resolved_name"] == "ASPIRIN"
    assert resolved["name_match"] == "exact"


def test_nearest_match_is_reported_not_passed_off_as_the_query():
    tool = _tool()
    responses = {
        "OpenTargets_get_drug_chembId_by_generic_name": _hits(
            ("CHEMBL112", "ACETAMINOPHEN")
        ),
        # PubChem resolving the same name is what makes this a supported
        # substitution rather than an unverified guess.
        "PubChem_get_CID_by_compound_name": {
            "status": "success",
            "data": {"IdentifierList": {"CID": [1983]}},
        },
        "RxNorm_find_rxcui": {"status": "success", "data": {}},
    }
    resolved = tool._resolve(
        lambda _s, name, _a, **_kw: responses[name], lambda *a: None, "Tylenol"
    )
    assert resolved["chembl_id"] == "CHEMBL112"
    assert resolved["name_match"] == "nearest"

    notes = tool._notes(
        {"query": {"drug": "Tylenol"}, "sources_failed": []}, resolved, ["identity"]
    )
    joined = " ".join(notes)
    assert "ACETAMINOPHEN" in joined and "Tylenol" in joined


def test_uncorroborated_near_match_is_marked_unverified():
    """OpenTargets returns a best guess for any string at all.

    'as"pirin' resolves to FLUTICASONE PROPIONATE and '2244' — which a caller
    could paste thinking it a PubChem CID — to BI-224436. What separates those
    from a real brand name is that Tylenol and adrenaline also resolve in
    PubChem, and a typo does not.
    """
    tool = _tool()

    def responses(cid_payload):
        return {
            "OpenTargets_get_drug_chembId_by_generic_name": _hits(
                ("CHEMBL1473", "FLUTICASONE PROPIONATE")
            ),
            "PubChem_get_CID_by_compound_name": cid_payload,
            "RxNorm_find_rxcui": {"status": "success", "data": {}},
        }

    no_cid = responses({"status": "success", "data": {}})
    guess = tool._resolve(
        lambda _s, name, _a, **_kw: no_cid[name], lambda *a: None, 'as"pirin'
    )
    assert guess["name_match"] == "unverified"

    with_cid = responses(
        {"status": "success", "data": {"IdentifierList": {"CID": [1983]}}}
    )
    corroborated = tool._resolve(
        lambda _s, name, _a, **_kw: with_cid[name], lambda *a: None, "Tylenol"
    )
    assert corroborated["name_match"] == "nearest"

    notes = " ".join(
        tool._notes(
            {"query": {"drug": 'as"pirin'}, "sources_failed": []}, guess, ["identity"]
        )
    )
    assert "nothing corroborates" in notes
    assert "unidentified" in notes


def test_chembl_identifier_input_skips_the_name_only_sources():
    tool = _tool()
    skipped = []
    resolved = tool._resolve(
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("no lookup for an id")),
        lambda s, r: skipped.append(s),
        "chembl25",
    )
    assert resolved["chembl_id"] == "CHEMBL25"
    assert resolved["name_match"] == "identifier"
    assert sorted(skipped) == ["pubchem", "rxnorm"]


def test_structure_cross_check_catches_two_different_molecules():
    """'penicillin' resolves to the potassium salt in ChEMBL and the free acid
    in PubChem — two molecules, one profile."""
    tool = _tool()
    chembl = {
        "molecule_structures": {"standard_inchi_key": "AAA-1", "canonical_smiles": "C"},
        "molecule_properties": {"full_molformula": "C9H8O4", "full_mwt": "180.16"},
    }
    mismatch = tool._structure(chembl, {"InChIKey": "BBB-2"})
    assert mismatch["inchikey_agreement"] is False
    # Numeric-looking strings are normalized so `weight > 100` works.
    assert mismatch["molecular_weight"] == 180.16

    agree = tool._structure(chembl, {"InChIKey": "AAA-1"})
    assert agree["inchikey_agreement"] is True

    # One source alone cannot corroborate, and must not claim to.
    assert tool._structure(chembl, {})["inchikey_agreement"] is None

    notes = " ".join(
        tool._notes(
            {
                "query": {"drug": "penicillin"},
                "structure": mismatch,
                "sources_failed": [],
            },
            {"name_match": "exact"},
            ["structure"],
        )
    )
    assert "different InChIKeys" in notes


def test_boxed_warning_sources_are_compared_not_merged():
    tool = _tool()
    agree = tool._safety(
        lambda *a: {
            "status": "success",
            "data": {"drug": {"drugWarnings": [{"warningType": "Black Box Warning"}]}},
        },
        lambda *a: None,
        {"black_box_warning": 1},
        "CHEMBL42",
    )
    assert agree["chembl_black_box_flag"] is True
    assert agree["boxed_warning_count"] == 1
    assert agree["sources_agree_on_boxed_warning"] is True

    # ChEMBL says boxed, OpenTargets returns none: a real disagreement, not a
    # value to silently prefer one side of.
    conflict = tool._safety(
        lambda *a: {"status": "success", "data": {"drug": {}}},
        lambda *a: None,
        {"black_box_warning": 1},
        "CHEMBL42",
    )
    assert conflict["sources_agree_on_boxed_warning"] is False
    notes = " ".join(
        tool._notes(
            {"query": {"drug": "x"}, "safety": conflict, "sources_failed": []},
            {"name_match": "exact"},
            ["safety"],
        )
    )
    assert "disagrees" in notes


def test_a_failed_warning_lookup_is_not_a_clean_safety_record():
    """Regression: an unknown ChEMBL id reported boxed_warning_count 0.

    Every source failed, yet the profile came back with a count of 0 and a note
    saying OpenTargets records no warning for this drug — an affirmative claim
    about drug safety that nothing supported.
    """
    tool = _tool()
    unanswered = tool._safety(
        lambda *a, **k: None,  # the call failed
        lambda *a: None,
        {},
        "CHEMBL99999999",
    )
    assert unanswered["warnings_checked"] is False
    assert unanswered["boxed_warning_count"] is None
    assert unanswered["sources_agree_on_boxed_warning"] is None

    notes = " ".join(
        tool._notes(
            {
                "query": {"drug": "x"},
                "safety": unanswered,
                "sources_failed": ["chembl: 404"],
            },
            {"name_match": "identifier"},
            ["safety"],
        )
    )
    assert "did not answer" in notes
    assert "clean safety record" in notes
    # The claim that applies only to a successful empty lookup must not appear.
    assert "records no warning" not in notes


def test_absent_warnings_are_not_evidence_of_safety():
    tool = _tool()
    none = tool._safety(
        lambda *a: {"status": "success", "data": {"drug": {}}},
        lambda *a: None,
        {"black_box_warning": 0},
        "CHEMBL25",
    )
    assert none["opentargets_warnings"] == []
    assert none["sources_agree_on_boxed_warning"] is True
    notes = " ".join(
        tool._notes(
            {"query": {"drug": "aspirin"}, "safety": none, "sources_failed": []},
            {"name_match": "exact"},
            ["safety"],
        )
    )
    assert "not evidence the drug is safe" in notes


def test_not_found_is_a_negative_answer_not_a_failure():
    """PubChem answers a name it does not hold with HTTP 404.

    That is the expected reply for an antibody — trastuzumab, adalimumab and
    heparin all produce it — so counting it as a failure inflated the failure
    count and implied the profile was degraded when nothing was missing.
    """
    assert _is_not_found("PubChem API returned HTTP 404") is True
    assert _is_not_found("No records found") is True
    # A genuine fault must stay a fault.
    assert _is_not_found("HTTP 500 internal server error") is False
    assert _is_not_found("connection timed out") is False
    assert _is_not_found("") is False


def test_sections_are_paid_for_only_when_requested():
    """Asking for 'mechanism' used to fetch the ChEMBL molecule and the PubChem
    properties as well, neither of which that section reads — so the documented
    saving from omitting a section did not exist."""
    assert _records_needed(["mechanism"]) == (False, False)
    assert _records_needed(["indications"]) == (False, False)
    assert _records_needed(["identity"]) == (True, False)
    assert _records_needed(["safety"]) == (True, False)
    assert _records_needed(["structure"]) == (True, True)
    assert _records_needed(list(SECTIONS)) == (True, True)


def test_empty_sections_is_an_error_not_a_request_for_everything():
    tool = _tool()
    empty = tool.run({"drug": "aspirin", "sections": []})
    assert empty["status"] == "error"
    assert "empty" in empty["error"]


def test_indications_lead_with_approved_uses():
    """Slicing the all-indications list returned an arbitrary subset.

    That endpoint gives every disease a drug has been studied in, unranked:
    aspirin's 186 rows begin with sudden sensorineural hearing loss and
    myocardial infarction is second, so the first 25 were not the 25 that
    matter. Metformin has 248 such rows and only 2 approved uses.
    """
    tool = _tool()

    def call(_source, tool_name, _args, **_kw):
        if tool_name == "OpenTargets_get_approved_indications_by_drug_chemblId":
            return {
                "status": "success",
                "data": {
                    "drug": {
                        "indications": {
                            "count": 2,
                            "rows": [
                                {"disease": {"id": "E1", "name": "type 2 diabetes"}},
                                {"disease": {"id": "E2", "name": "diabetes mellitus"}},
                            ],
                        }
                    }
                },
            }
        return {
            "status": "success",
            "data": {"drug": {"indications": {"count": 248, "rows": []}}},
        }

    out = tool._indications(call, lambda *a: None, "CHEMBL1431")
    assert [x["disease"] for x in out["approved"]] == [
        "type 2 diabetes",
        "diabetes mellitus",
    ]
    assert out["approved_count"] == 2
    assert out["total_investigated_count"] == 248
    assert out["truncated"] is False

    notes = " ".join(
        tool._notes(
            {"query": {"drug": "metformin"}, "indications": out, "sources_failed": []},
            {"name_match": "exact"},
            ["indications"],
        )
    )
    # Being studied in 248 diseases must not read as being approved for them.
    assert "not evidence of efficacy" in notes

    # With no ChEMBL id the section is empty and says why, rather than guessing.
    skipped = []
    empty = tool._indications(call, lambda s, r: skipped.append(s), None)
    assert empty["approved"] == [] and empty["approved_count"] is None
    assert skipped == ["opentargets"]


def test_as_number_normalizes_only_what_is_numeric():
    # ChEMBL sends max_phase as '4.0'; `max_phase == 4` must hold.
    assert _as_number("4.0") == 4
    assert _as_number("180.16") == 180.16
    assert _as_number(1950) == 1950
    assert _as_number(None) is None
    # A non-numeric field is left exactly as it came.
    assert _as_number("Small molecule") == "Small molecule"


def test_run_rejects_bad_input_without_raising():
    tool = _tool()
    assert tool.run({})["status"] == "error"
    assert tool.run({"drug": "   "})["status"] == "error"
    bad = tool.run({"drug": "aspirin", "sections": ["nope"]})
    assert bad["status"] == "error"
    assert "nope" in bad["error"]
