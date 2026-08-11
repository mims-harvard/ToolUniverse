"""Regression guard for Fix-R81A-1: CPIC_get_recommendations built its
per-drug filter as a hardcoded ``drugid=eq.RxNorm:{rxnormid}``, assuming
every CPIC drug identifier lives in the RxNorm namespace.

It does not. CPIC's /recommendation.drugid is a *namespaced* identifier, and
a live census of api.cpicpgx.org (324 drugs; 170 carrying a guideline) found
167 RxNorm, 2 ATC and 1 Drugbank among the guideline-bearing drugs. The bad
assumption failed in two opposite and equally silent directions:

  (a) FALSE NEGATIVE -- gentamicin has an rxnormid (1596450) but its drugid
      is ``ATC:D06AX07``, so ``eq.RxNorm:1596450`` matched 0 of the 33 rows
      on MT-RNR1 aminoglycoside guideline 826283. The tool then asserted
      "...none specifically for 'gentamicin'" -- a confident empty answer for
      the archetypal ototoxic aminoglycoside, exactly the query run before
      dosing a patient carrying m.1555A>G. The 3 rows exist and carry the
      "Avoid aminoglycoside antibiotics" guidance.

  (b) FALSE POSITIVE -- lumiracoxib and ramosetron have a NULL rxnormid, so
      the ``if rxnorm_id:`` guard was falsy and NO drug filter was applied.
      ``{"drug": "lumiracoxib"}`` returned all 42 rows of NSAID guideline
      110058, every one of which belongs to a *different* NSAID, presented
      as lumiracoxib's own recommendations.

These tests are fully offline -- ``requests.get`` is patched -- and pin the
namespace behaviour in both directions, including that RxNorm-namespaced
drugs keep producing a byte-identical filter string.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.cpic_search_pairs_tool import CPICGetRecommendationsTool

pytestmark = pytest.mark.unit


def _resp(json_body):
    r = MagicMock()
    r.json.return_value = json_body
    r.raise_for_status.return_value = None
    return r


def _tool():
    return CPICGetRecommendationsTool({"name": "CPIC_get_recommendations"})


# The 3 real MT-RNR1 rows CPIC serves for drugid=ATC:D06AX07 on guideline
# 826283, trimmed to the fields these assertions care about.
_GENTAMICIN_ROWS = [
    {
        "id": 8479708,
        "guidelineid": 826283,
        "drugid": "ATC:D06AX07",
        "implications": {
            "MT-RNR1": (
                "Very high risk of developing hearing loss if administered "
                "an aminoglycoside antibiotic."
            )
        },
        "drugrecommendation": (
            "Avoid aminoglycoside anitbiotics unless the high risk of "
            "permanent hearing loss is outweighed by the severity of "
            "infection and lack of safe or effective alternative therapies."
        ),
        "drug": {"name": "gentamicin"},
    },
    {
        "id": 8479709,
        "guidelineid": 826283,
        "drugid": "ATC:D06AX07",
        "implications": {
            "MT-RNR1": (
                "Normal risk of developing hearing loss if administered an "
                "aminoglycoside antibiotic."
            )
        },
        "drugrecommendation": (
            "Use aminoglycoside antibiotics at standard doses for the "
            "shortest feasible course with therapeutic dose monitoring."
        ),
        "drug": {"name": "gentamicin"},
    },
    {
        "id": 8479710,
        "guidelineid": 826283,
        "drugid": "ATC:D06AX07",
        "implications": {
            "MT-RNR1": (
                "Weak or no evidence for an increased risk of MT-RNR1 "
                "associated hearing loss if administered an aminoglycoside "
                "antibiotic."
            )
        },
        "drugrecommendation": (
            "Use aminoglycoside antibiotics at standard doses for the "
            "shortest feasible course with therapeutic dose monitoring."
        ),
        "drug": {"name": "gentamicin"},
    },
]


class _FakeCPIC:
    """Minimal stand-in for CPIC's PostgREST API.

    Serves /drug from a single row and /recommendation from a row list,
    honouring the ``drugid=eq.<id>`` filter exactly as PostgREST would --
    so a wrong namespace genuinely yields zero rows rather than being
    papered over by a mock that ignores the filter.
    """

    def __init__(self, drug_row, recommendation_rows):
        self.drug_row = drug_row
        self.recommendation_rows = recommendation_rows
        self.drugid_filters = []

    def __call__(self, url, params=None, **kwargs):
        params = params or {}
        if url.endswith("/drug"):
            return _resp([self.drug_row])
        drugid_filter = params.get("drugid")
        self.drugid_filters.append(drugid_filter)
        rows = self.recommendation_rows
        if drugid_filter is not None:
            wanted = drugid_filter.split("eq.", 1)[1]
            rows = [r for r in rows if r.get("drugid") == wanted]
        return _resp(rows)


class TestNonRxNormDrugidResolves:
    """Shape (a): drugid in a non-RxNorm namespace must still match."""

    def test_gentamicin_atc_drugid_returns_its_mt_rnr1_rows(self):
        fake = _FakeCPIC(
            {"name": "gentamicin", "guidelineid": 826283, "drugid": "ATC:D06AX07"},
            _GENTAMICIN_ROWS,
        )
        with patch(
            "tooluniverse.cpic_search_pairs_tool.requests.get", side_effect=fake
        ):
            result = _tool().run({"drug": "gentamicin"})

        assert result["status"] == "success"
        data = result["data"]
        assert data["guideline_id"] == 826283
        # The whole point: 3 rows, not the old confidently-empty answer.
        assert data["count"] == 3
        assert len(data["recommendations"]) == 3
        # And no note asserting an absence that isn't real.
        assert "note" not in data

        # The filter must have used CPIC's own drugid, NOT a reconstructed
        # RxNorm one. gentamicin's rxnormid (1596450) appears nowhere in
        # CPIC's recommendation table.
        assert fake.drugid_filters == ["eq.ATC:D06AX07"]
        assert "eq.RxNorm:1596450" not in fake.drugid_filters

    def test_gentamicin_rows_carry_mt_rnr1_avoid_aminoglycoside_guidance(self):
        fake = _FakeCPIC(
            {"name": "gentamicin", "guidelineid": 826283, "drugid": "ATC:D06AX07"},
            _GENTAMICIN_ROWS,
        )
        with patch(
            "tooluniverse.cpic_search_pairs_tool.requests.get", side_effect=fake
        ):
            rows = _tool().run({"drug": "gentamicin"})["data"]["recommendations"]

        assert all("MT-RNR1" in row["implications"] for row in rows)
        assert all(row["drug"]["name"] == "gentamicin" for row in rows)
        # The high-risk m.1555A>G row must carry the avoid-the-drug action.
        high_risk = [
            r for r in rows if "Very high risk" in r["implications"]["MT-RNR1"]
        ]
        assert len(high_risk) == 1
        assert "Avoid aminoglycoside" in high_risk[0]["drugrecommendation"]


class TestNullRxnormidNoLongerLeaksOtherDrugsRows:
    """Shape (b): a NULL rxnormid used to disable the drug filter entirely."""

    def test_lumiracoxib_does_not_return_other_nsaids_rows(self):
        other_nsaid_rows = [
            {
                "id": 8480112,
                "guidelineid": 110058,
                "drugid": "RxNorm:140587",
                "drug": {"name": "celecoxib"},
            },
            {
                "id": 8480113,
                "guidelineid": 110058,
                "drugid": "RxNorm:5640",
                "drug": {"name": "ibuprofen"},
            },
        ]
        fake = _FakeCPIC(
            {"name": "lumiracoxib", "guidelineid": 110058, "drugid": "ATC:M01AH06"},
            other_nsaid_rows,
        )
        with patch(
            "tooluniverse.cpic_search_pairs_tool.requests.get", side_effect=fake
        ):
            result = _tool().run({"drug": "lumiracoxib"})

        data = result["data"]
        # CPIC genuinely has no lumiracoxib rows on this guideline; it must
        # NOT inherit celecoxib's or ibuprofen's prescribing guidance.
        assert data["count"] == 0
        names = [r["drug"]["name"] for r in data["recommendations"]]
        assert "celecoxib" not in names
        assert "ibuprofen" not in names
        # A drug filter must actually have been sent.
        assert fake.drugid_filters[0] == "eq.ATC:M01AH06"

    def test_genuine_absence_note_still_fires_and_names_the_identifier(self):
        fake = _FakeCPIC(
            {"name": "lumiracoxib", "guidelineid": 110058, "drugid": "ATC:M01AH06"},
            [
                {
                    "id": 1,
                    "guidelineid": 110058,
                    "drugid": "RxNorm:140587",
                    "drug": {"name": "celecoxib"},
                }
            ],
        )
        with patch(
            "tooluniverse.cpic_search_pairs_tool.requests.get", side_effect=fake
        ):
            note = _tool().run({"drug": "lumiracoxib"})["data"]["note"]

        assert "none specifically for 'lumiracoxib'" in note
        # The absence is only credible because it was established against
        # CPIC's real identifier -- the note must say which one.
        assert "ATC:M01AH06" in note


class TestRxNormNamespacedDrugsAreUnchanged:
    """RxNorm drugs (167 of the 170 guideline-bearing ones) must be untouched."""

    def test_filter_string_is_byte_identical_to_the_old_hardcoded_form(self):
        # Old code built this from rxnormid as f"eq.RxNorm:{rxnormid}";
        # new code builds it from drugid as f"eq.{drugid}". For every
        # RxNorm-namespaced drug, drugid == "RxNorm:" + rxnormid, so the
        # two strings are identical.
        rows = [
            {
                "id": 1,
                "guidelineid": 100416,
                "drugid": "RxNorm:2670",
                "drug": {"name": "codeine"},
            }
        ]
        fake = _FakeCPIC(
            {"name": "codeine", "guidelineid": 100416, "drugid": "RxNorm:2670"},
            rows,
        )
        with patch(
            "tooluniverse.cpic_search_pairs_tool.requests.get", side_effect=fake
        ):
            result = _tool().run({"drug": "codeine"})

        assert fake.drugid_filters == ["eq.RxNorm:2670"]
        assert result["data"]["count"] == 1
        assert result["data"]["recommendations"][0]["drug"]["name"] == "codeine"

    def test_multi_drug_guideline_still_filters_to_the_requested_drug(self):
        rows = [
            {
                "id": 1,
                "guidelineid": 100416,
                "drugid": "RxNorm:2670",
                "drug": {"name": "codeine"},
            },
            {
                "id": 2,
                "guidelineid": 100416,
                "drugid": "RxNorm:10689",
                "drug": {"name": "tramadol"},
            },
        ]
        fake = _FakeCPIC(
            {"name": "codeine", "guidelineid": 100416, "drugid": "RxNorm:2670"},
            rows,
        )
        with patch(
            "tooluniverse.cpic_search_pairs_tool.requests.get", side_effect=fake
        ):
            result = _tool().run({"drug": "codeine"})

        names = [r["drug"]["name"] for r in result["data"]["recommendations"]]
        assert names == ["codeine"]


class TestUnresolvableDrugidIsDisclosedNotAsserted:
    """If no drugid can be resolved the tool cannot filter -- it must say so
    rather than presenting the whole guideline as this drug's guidance, and
    must never assert absence it did not establish."""

    def test_unfiltered_rows_are_flagged_as_possibly_other_drugs(self):
        rows = [
            {
                "id": 1,
                "guidelineid": 110058,
                "drugid": "RxNorm:140587",
                "drug": {"name": "celecoxib"},
            }
        ]
        # No 'drugid' key at all in the /drug row.
        fake = _FakeCPIC({"name": "mysterydrug", "guidelineid": 110058}, rows)
        with patch(
            "tooluniverse.cpic_search_pairs_tool.requests.get", side_effect=fake
        ):
            result = _tool().run({"drug": "mysterydrug"})

        data = result["data"]
        assert fake.drugid_filters == [None]  # no filter could be sent
        note = data["note"]
        assert "could NOT be filtered" in note
        assert "may" in note and "cover other drugs" in note
        # Must not claim CPIC has no rows for the drug -- that was never tested.
        assert "none specifically for" not in note

    def test_no_absence_claim_when_identifier_is_unknown_and_rows_are_empty(self):
        fake = _FakeCPIC({"name": "mysterydrug", "guidelineid": 999999}, [])
        with patch(
            "tooluniverse.cpic_search_pairs_tool.requests.get", side_effect=fake
        ):
            note = _tool().run({"drug": "mysterydrug"})["data"]["note"]

        # Falls back to the generic no-table note, never the drug-specific
        # "none specifically for X" claim, which we could not have verified.
        assert "none specifically for" not in note
        assert "No discrete recommendations found" in note


class TestGuidelineIdPathUnaffected:
    """Passing guideline_id directly sends no drug filter, as before."""

    def test_no_drug_filter_and_no_nameerror(self):
        rows = [
            {
                "id": 1,
                "guidelineid": 826283,
                "drugid": "ATC:D06AX07",
                "drug": {"name": "gentamicin"},
            }
        ]
        fake = _FakeCPIC({}, rows)
        with patch(
            "tooluniverse.cpic_search_pairs_tool.requests.get", side_effect=fake
        ):
            result = _tool().run({"guideline_id": 826283, "limit": 3})

        assert result["status"] == "success"
        assert fake.drugid_filters == [None]
        assert result["data"]["count"] == 1

    def test_empty_guideline_by_id_does_not_emit_a_drug_specific_note(self):
        fake = _FakeCPIC({}, [])
        with patch(
            "tooluniverse.cpic_search_pairs_tool.requests.get", side_effect=fake
        ):
            result = _tool().run({"guideline_id": 100425})

        note = result["data"]["note"]
        assert "none specifically for" not in note
        assert "could NOT be filtered" not in note
