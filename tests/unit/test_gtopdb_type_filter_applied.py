"""Regression guard for Fix-R30-GtoPdb-type in gtopdb_tool.py: the `type`
filter on GtoPdb_search_ligands (and its sibling GtoPdb_search_targets) was
accepted, forwarded, and then completely ignored, so the query executed was
never the query submitted.

Reproduction that motivated the fix::

    tu run GtoPdb_search_ligands '{"name":"semaglutide","type":"NotARealType"}'
    -> status success, 1 record: ligandId 9724, name "semaglutide", type "Peptide"

A garbage type value changed nothing; neither did a real-but-wrong one. The
result sets were byte-identical with `type` omitted, wrong, or nonsense.

Established upstream by curl (2026-08-10), i.e. this is GtoPdb's behaviour,
not a transport bug in the wrapper::

    /services/ligands?name=semaglutide                        -> 1 rec, type "Peptide"
    /services/ligands?name=semaglutide&type=Synthetic organic -> the SAME record
    /services/ligands?name=semaglutide&type=NotARealType      -> the SAME record
    /services/targets?name=serotonin                          -> 19 recs (gpcr/lgic/transporter)
    /services/targets?name=serotonin&type=GPCR                -> the SAME 19 records

GtoPdb drops ?type= whenever ?name= is present. Used alone it does filter, but
only over a vocabulary that is neither the record `type` vocabulary nor the enum
ToolUniverse used to document::

    /services/ligands?type=Peptide            -> HTTP 404 "No ligands found"
    /services/ligands?type=Endogenous peptide -> HTTP 404 (GtoPdb's own docs list it)
    /services/targets?type=Ion channel        -> HTTP 404 (ToolUniverse documented it)

The old test_examples entry ``{"name": "dopamine", "type": "Endogenous
peptide"}`` passed only because the filter was ignored -- dopamine is a
Metabolite, and the call returned Peptide/Metabolite/Synthetic organic records
that did not match the requested filter. It asserted nothing.

The fix filters client-side against each record's own `type` field (or boolean
flag, for 'Approved'/'Withdrawn'/'Labelled') and validates the requested value
at input against the vocabulary GtoPdb really uses. These tests mock the HTTP
layer -- no network -- with a fixed upstream payload of mixed `type` values,
exactly as GtoPdb returns when it ignores the filter.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.gtopdb_tool import GtoPdbRESTTool

pytestmark = pytest.mark.unit

LIGANDS_ENDPOINT = "https://www.guidetopharmacology.org/services/ligands"
TARGETS_ENDPOINT = "https://www.guidetopharmacology.org/services/targets"

# Real shape of GET /services/ligands?name=dopamine (captured live 2026-08-10).
# GtoPdb returns all four records regardless of any `type=` supplied alongside
# `name=`, which is precisely the defect under guard.
_DOPAMINE_PAYLOAD = [
    {
        "ligandId": 13048,
        "name": "cerebral dopamine neurotrophic factor",
        "type": "Peptide",
        "approved": False,
        "withdrawn": False,
        "labelled": False,
    },
    {
        "ligandId": 940,
        "name": "dopamine",
        "type": "Metabolite",
        "approved": True,
        "withdrawn": False,
        "labelled": False,
    },
    {
        "ligandId": 5552,
        "name": "N-oleoyldopamine",
        "type": "Metabolite",
        "approved": False,
        "withdrawn": False,
        "labelled": False,
    },
    {
        "ligandId": 4261,
        "name": "NADA",
        "type": "Synthetic organic",
        "approved": False,
        "withdrawn": False,
        "labelled": True,
    },
]

# Real shape of GET /services/targets?name=serotonin (trimmed to 5 of 19).
_SEROTONIN_TARGETS = [
    {"targetId": 928, "name": "SERT", "type": "transporter"},
    {"targetId": 12, "name": "5-HT7 receptor", "type": "gpcr"},
    {"targetId": 11, "name": "5-HT6 receptor", "type": "gpcr"},
    {"targetId": 377, "name": "5-HT3E", "type": "lgic"},
    {"targetId": 2486, "name": "dopamine beta-hydroxylase", "type": "enzyme"},
]


def _tool(endpoint):
    return GtoPdbRESTTool(
        {"name": "GtoPdb_test", "fields": {"endpoint": endpoint, "params": {}}}
    )


def _resp(payload, status=200):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = payload
    r.text = ""
    return r


def _run(endpoint, arguments, payload):
    """Run the tool with the HTTP layer stubbed, returning (result, urls_called)."""
    calls = []

    def fake(session, method, url, **kwargs):
        calls.append(url)
        return _resp(payload)

    with patch("tooluniverse.gtopdb_tool.request_with_retry", side_effect=fake):
        result = _tool(endpoint).run(arguments)
    return result, calls


# ---------------------------------------------------------------------------
# (a) a `type` filter actually removes non-matching records
# ---------------------------------------------------------------------------


class TestTypeFilterRemovesNonMatchingRecords:
    def test_ligand_type_filters_out_other_types(self):
        result, _ = _run(
            LIGANDS_ENDPOINT,
            {"name": "dopamine", "type": "Metabolite"},
            _DOPAMINE_PAYLOAD,
        )
        assert result["status"] == "success"
        assert [r["ligandId"] for r in result["data"]] == [940, 5552]
        assert {r["type"] for r in result["data"]} == {"Metabolite"}
        assert result["count"] == 2

    def test_semaglutide_reproduction_peptide_filter_keeps_the_record(self):
        """The exact record from the reproduction: type='Peptide' must keep it."""
        payload = [
            {
                "ligandId": 9724,
                "name": "semaglutide",
                "type": "Peptide",
                "approved": True,
            }
        ]
        result, _ = _run(
            LIGANDS_ENDPOINT, {"name": "semaglutide", "type": "Peptide"}, payload
        )
        assert [r["ligandId"] for r in result["data"]] == [9724]

    def test_semaglutide_reproduction_wrong_type_now_returns_nothing(self):
        """'Synthetic organic' is a real GtoPdb type but not semaglutide's.

        Before the fix this returned the semaglutide record unchanged.
        """
        payload = [
            {
                "ligandId": 9724,
                "name": "semaglutide",
                "type": "Peptide",
                "approved": True,
            }
        ]
        result, _ = _run(
            LIGANDS_ENDPOINT,
            {"name": "semaglutide", "type": "Synthetic organic"},
            payload,
        )
        assert result["status"] == "success"
        assert result["data"] == []
        assert result["count"] == 0

    def test_type_is_matched_case_insensitively(self):
        result, _ = _run(
            LIGANDS_ENDPOINT,
            {"name": "dopamine", "type": "metabolite"},
            _DOPAMINE_PAYLOAD,
        )
        assert [r["ligandId"] for r in result["data"]] == [940, 5552]

    def test_flag_pseudo_types_match_boolean_record_fields(self):
        approved, _ = _run(
            LIGANDS_ENDPOINT,
            {"name": "dopamine", "type": "Approved"},
            _DOPAMINE_PAYLOAD,
        )
        assert [r["ligandId"] for r in approved["data"]] == [940]

        labelled, _ = _run(
            LIGANDS_ENDPOINT,
            {"name": "dopamine", "type": "Labelled"},
            _DOPAMINE_PAYLOAD,
        )
        assert [r["ligandId"] for r in labelled["data"]] == [4261]

    def test_type_is_not_forwarded_upstream_when_a_name_search_is_present(self):
        """GtoPdb ignores ?type= alongside ?name=; sending it only misleads."""
        _, calls = _run(
            LIGANDS_ENDPOINT,
            {"name": "dopamine", "type": "Metabolite"},
            _DOPAMINE_PAYLOAD,
        )
        assert calls, "expected at least one upstream request"
        assert all("type=" not in u for u in calls), calls
        assert any("name=dopamine" in u for u in calls), calls

    def test_result_discloses_that_the_filter_was_enforced_client_side(self):
        result, _ = _run(
            LIGANDS_ENDPOINT,
            {"name": "dopamine", "type": "Metabolite"},
            _DOPAMINE_PAYLOAD,
        )
        assert result["type_filter"]["requested"] == "Metabolite"
        assert result["type_filter"]["enforced"] == "client-side"
        assert result["type_filter"]["records_scanned"] == 4
        assert result["type_filter"]["records_matched"] == 2


class TestSiblingTargetSearchFiltersToo:
    """GtoPdb_search_targets had the identical defect: ?type=GPCR alongside
    ?name=serotonin returned transporters and ion channels unchanged."""

    def test_target_type_filters_out_other_types(self):
        result, _ = _run(
            TARGETS_ENDPOINT,
            {"name": "serotonin", "type": "GPCR"},
            _SEROTONIN_TARGETS,
        )
        assert [r["targetId"] for r in result["data"]] == [12, 11]
        assert {r["type"] for r in result["data"]} == {"gpcr"}

    def test_ion_channel_umbrella_covers_all_three_record_types(self):
        result, _ = _run(
            TARGETS_ENDPOINT,
            {"name": "serotonin", "type": "Ion channel"},
            _SEROTONIN_TARGETS,
        )
        assert [r["targetId"] for r in result["data"]] == [377]

    def test_target_type_not_forwarded_upstream_with_a_name_search(self):
        _, calls = _run(
            TARGETS_ENDPOINT,
            {"name": "serotonin", "type": "GPCR"},
            _SEROTONIN_TARGETS,
        )
        assert all("type=" not in u for u in calls), calls


# ---------------------------------------------------------------------------
# (b) an invalid `type` is rejected at input rather than silently ignored
# ---------------------------------------------------------------------------


class TestInvalidTypeRejectedAtInput:
    def test_garbage_ligand_type_is_an_error_not_an_unfiltered_result(self):
        """The headline reproduction: NotARealType used to return everything."""
        result, calls = _run(
            LIGANDS_ENDPOINT,
            {"name": "semaglutide", "type": "NotARealType"},
            _DOPAMINE_PAYLOAD,
        )
        assert result["status"] == "error"
        assert "NotARealType" in result["error"]
        assert "data" not in result
        # Rejected before any request went out.
        assert calls == []

    def test_error_lists_the_real_vocabulary(self):
        result, _ = _run(
            LIGANDS_ENDPOINT, {"name": "x", "type": "Synthetic"}, _DOPAMINE_PAYLOAD
        )
        assert result["status"] == "error"
        for expected in (
            "Synthetic organic",
            "Peptide",
            "Natural product",
            "Metabolite",
            "Antibody",
            "Nucleic acid",
            "Inorganic",
            "Approved",
            "Withdrawn",
            "Labelled",
        ):
            assert expected in result["valid_types"]

    def test_documented_but_dead_gtopdb_value_is_rejected_with_a_pointer(self):
        """'Endogenous peptide' is in GtoPdb's own docs but matches no record
        (HTTP 404 upstream). It was the old, misleading test_examples value."""
        result, calls = _run(
            LIGANDS_ENDPOINT,
            {"name": "dopamine", "type": "Endogenous peptide"},
            _DOPAMINE_PAYLOAD,
        )
        assert result["status"] == "error"
        assert "Peptide" in result["error"]
        assert calls == []

    def test_target_enum_values_that_404_upstream_are_accepted_as_aliases(self):
        """'Nuclear receptor' and 'Catalytic receptor' were ToolUniverse's own
        documented values; they 404 upstream, so they map to NHR /
        catalytic_receptor rather than being rejected."""
        payload = [
            {"targetId": 1, "name": "ER-alpha", "type": "nhr"},
            {"targetId": 2, "name": "EGFR", "type": "catalytic_receptor"},
        ]
        nhr, _ = _run(
            TARGETS_ENDPOINT, {"name": "x", "type": "Nuclear receptor"}, payload
        )
        assert [r["targetId"] for r in nhr["data"]] == [1]

        cat, _ = _run(
            TARGETS_ENDPOINT, {"name": "x", "type": "catalytic_receptor"}, payload
        )
        assert [r["targetId"] for r in cat["data"]] == [2]

    def test_invalid_target_type_is_rejected(self):
        result, calls = _run(
            TARGETS_ENDPOINT,
            {"name": "serotonin", "type": "Kinase"},
            _SEROTONIN_TARGETS,
        )
        assert result["status"] == "error"
        assert "GPCR" in result["valid_types"]
        assert calls == []


# ---------------------------------------------------------------------------
# (c) omitting `type` returns everything unchanged
# ---------------------------------------------------------------------------


class TestNoTypeMeansNoFiltering:
    def test_ligand_search_without_type_returns_all_records(self):
        result, calls = _run(LIGANDS_ENDPOINT, {"name": "dopamine"}, _DOPAMINE_PAYLOAD)
        assert result["status"] == "success"
        assert [r["ligandId"] for r in result["data"]] == [13048, 940, 5552, 4261]
        assert "type_filter" not in result
        assert any("name=dopamine" in u for u in calls)

    def test_target_search_without_type_returns_all_records(self):
        result, _ = _run(TARGETS_ENDPOINT, {"name": "serotonin"}, _SEROTONIN_TARGETS)
        assert len(result["data"]) == len(_SEROTONIN_TARGETS)
        assert "type_filter" not in result

    def test_empty_string_type_is_treated_as_omitted(self):
        result, _ = _run(
            LIGANDS_ENDPOINT, {"name": "dopamine", "type": ""}, _DOPAMINE_PAYLOAD
        )
        assert result["status"] == "success"
        assert len(result["data"]) == 4


# ---------------------------------------------------------------------------
# (d) `approved` -- a total no-op upstream, verified by curl:
#     /services/ligands?approved=true  -> all 13856 ligands
#     /services/ligands?approved=false -> the same 13856 ligands
#     so it too must be enforced client-side.
# ---------------------------------------------------------------------------


class TestApprovedFilter:
    def test_approved_true_keeps_only_approved_records(self):
        result, _ = _run(
            LIGANDS_ENDPOINT, {"name": "dopamine", "approved": True}, _DOPAMINE_PAYLOAD
        )
        assert [r["ligandId"] for r in result["data"]] == [940]
        assert result["approved_filter"]["records_scanned"] == 4
        assert result["approved_filter"]["records_matched"] == 1

    def test_approved_true_is_not_forwarded_upstream(self):
        _, calls = _run(
            LIGANDS_ENDPOINT, {"name": "dopamine", "approved": True}, _DOPAMINE_PAYLOAD
        )
        assert all("approved=" not in u for u in calls), calls

    def test_approved_false_means_all_ligands_as_documented(self):
        """The parameter has always been documented as 'approved drugs only
        (true) or all ligands (false/omit)', so false is not a filter."""
        result, _ = _run(
            LIGANDS_ENDPOINT, {"name": "dopamine", "approved": False}, _DOPAMINE_PAYLOAD
        )
        assert len(result["data"]) == 4
        assert "approved_filter" not in result

    def test_approved_combines_with_type(self):
        result, _ = _run(
            LIGANDS_ENDPOINT,
            {"name": "dopamine", "type": "Metabolite", "approved": True},
            _DOPAMINE_PAYLOAD,
        )
        assert [r["ligandId"] for r in result["data"]] == [940]

    def test_approved_alone_uses_the_one_server_side_filter_gtopdb_honours(self):
        """With no name search there is nothing to narrow the fetch, so push
        ?type=Approved (the only approval filter GtoPdb honours) upstream
        instead of pulling all 13856 ligands."""
        _, calls = _run(LIGANDS_ENDPOINT, {"approved": True}, _DOPAMINE_PAYLOAD)
        assert any("type=Approved" in u for u in calls), calls


# ---------------------------------------------------------------------------
# Server-side push-down is an optimisation only: the client-side filter must
# still run, so a stale/ignored server response can never leak through.
# ---------------------------------------------------------------------------


class TestServerSidePushDownStillFiltersClientSide:
    def test_type_only_query_pushes_supported_value_upstream(self):
        _, calls = _run(LIGANDS_ENDPOINT, {"type": "Metabolite"}, _DOPAMINE_PAYLOAD)
        assert any("type=Metabolite" in u for u in calls), calls

    def test_type_only_query_still_filters_a_non_compliant_response(self):
        result, _ = _run(LIGANDS_ENDPOINT, {"type": "Metabolite"}, _DOPAMINE_PAYLOAD)
        assert [r["ligandId"] for r in result["data"]] == [940, 5552]

    def test_peptide_is_never_pushed_upstream_because_it_404s_there(self):
        _, calls = _run(LIGANDS_ENDPOINT, {"type": "Peptide"}, _DOPAMINE_PAYLOAD)
        assert all("type=" not in u for u in calls), calls

    def test_peptide_only_query_still_filters_client_side(self):
        result, _ = _run(LIGANDS_ENDPOINT, {"type": "Peptide"}, _DOPAMINE_PAYLOAD)
        assert [r["ligandId"] for r in result["data"]] == [13048]
