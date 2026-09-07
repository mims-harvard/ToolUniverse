"""FAERS_calculate_disproportionality must say which cohort its ROR describes.

The drug arm of the 2x2 table is a union over FAERS_DRUG_NAME_FIELDS, two
thirds of which are openFDA's SPL annotation rather than the reported product
text. openFDA tags a report with EVERY brand and generic name registered for
the active ingredient of a product the report named, so a brand-name query
collects every sibling product sharing that ingredient.

The count tools already disclosed this. The inferential path did not, and that
is the worse omission: it attaches a confidence interval to the result.

Measured live 2026-08-12 against openFDA, CYANOKIT (a cyanide antidote) vs DEATH:

    union cohort         a=50 b=4,069  ROR 0.287 [0.217, 0.379]
    reported-name cohort a=12 b=226    ROR 1.24  [0.694, 2.216]

CYANOKIT has 4,119 reports in the union and 238 under the reported name; the
top names in that union are HYDROXOCOBALAMIN 3,882, ATORVASTATIN 775,
BISOPROLOL 538 -- vitamin B12 supplementation and its patients' polypharmacy.
The union interval lies entirely below 1, so the tool told a poison control
physician that death is reported disproportionately LESS often for a cyanide
antidote. Restricted to reports that named CYANOKIT the answer is inconclusive.
Not a shifted number: the opposite verdict.

The union stays the analysed cohort, because the size of the gap cannot
distinguish brand contamination from a generic correctly collecting its own
brands -- TOFACITINIB is 93.0% non-naming and CYANOKIT is 94.2%, and the extra
reports are genuine exposure in the first case and a different drug in the
second. What this test pins is that the split is measured and published, and
that the restricted ROR is offered alongside it.

Offline: every count lookup is patched, so no openFDA request is made.
"""

from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit

# The live CYANOKIT / DEATH figures above.
A_UNION = 50
DRUG_TOTAL_UNION = 4119
EVENT_TOTAL = 849880
DB_TOTAL = 20692690
NAMED_TOTAL = 238
A_NAMED = 12


def _tool():
    from tooluniverse.faers_analytics_tool import FAERSAnalyticsTool

    return FAERSAnalyticsTool({"name": "t", "type": "FAERSAnalyticsTool"})


def _run(named_total=NAMED_TOTAL, a_named=A_NAMED, drug_total=DRUG_TOTAL_UNION):
    """Run the real calculation, answering each probe by what it asked for.

    Keyed on the arguments rather than call order so that adding or reordering a
    probe cannot silently feed one lookup's answer to a different lookup.
    """
    tool = _tool()

    def fake_count(drug_name=None, adverse_event=None, reported_name_only=False):
        if reported_name_only:
            return a_named if adverse_event else named_total
        if drug_name and adverse_event:
            return A_UNION
        if drug_name:
            return drug_total
        if adverse_event:
            return EVENT_TOTAL
        return DB_TOTAL

    with patch.object(tool, "_get_faers_count", side_effect=fake_count):
        return tool._calculate_disproportionality(
            {"drug_name": "CYANOKIT", "adverse_event": "DEATH"}
        )


class TestCohortScopeIsPublished:
    def test_split_between_named_and_name_resolved_reports(self):
        scope = _run()["cohort_scope"]
        assert scope["reports_naming_queried_drug"] == 238
        assert scope["reports_matched_by_name_resolution_only"] == 3881
        assert scope["percent_matched_by_name_resolution_only"] == 94.2

    def test_note_names_the_cohort_the_verdict_was_reached_over(self):
        """The headline verdict says "for this drug"; 94% of it is not."""
        note = _run()["note"]
        assert "COHORT:" in note
        assert "238" in note and "4,119" in note
        assert "active-ingredient population" in note

    def test_headline_metrics_are_untouched(self):
        """The disclosure is additive -- no existing figure moves."""
        result = _run()
        assert result["contingency_table"]["a_drug_and_event"] == A_UNION
        assert result["contingency_table"]["b_drug_no_event"] == 4069
        assert result["metrics"]["ROR"]["value"] == 0.287
        assert result["signal_detection"]["signal_detected"] is False


class TestReportedNameOnlyArm:
    def test_ror_restricted_to_reports_naming_the_drug(self):
        arm = _run()["cohort_scope"]["reported_name_only_analysis"]
        assert arm["ROR"]["value"] == 1.24
        assert arm["ROR"]["ci_95_lower"] == 0.694
        assert arm["ROR"]["ci_95_upper"] == 2.216

    def test_cells_are_rebuilt_from_this_arms_own_a(self):
        """The four cells must still partition the database total.

        Reusing `c` and `d` from the union arm would leave a table that sums to
        something other than FAERS, and whose `c` double-counted the reports
        this arm just removed from `a`.
        """
        table = _run()["cohort_scope"]["reported_name_only_analysis"][
            "contingency_table"
        ]
        assert table["a_drug_and_event"] == A_NAMED
        assert table["b_drug_no_event"] == NAMED_TOTAL - A_NAMED
        assert table["c_no_drug_event"] == EVENT_TOTAL - A_NAMED
        assert sum(table.values()) == DB_TOTAL

    def test_the_two_arms_reach_opposite_verdicts(self):
        """The reason this block exists, stated as an assertion.

        The union arm's interval lies entirely below 1 -- a confident "reported
        LESS often". The restricted arm's interval spans 1 -- inconclusive.
        """
        result = _run()
        assert result["metrics"]["ROR"]["ci_95_upper"] < 1.0
        arm = result["cohort_scope"]["reported_name_only_analysis"]
        assert arm["ROR"]["ci_95_lower"] < 1.0 < arm["ROR"]["ci_95_upper"]

    def test_an_empty_cell_publishes_the_table_without_a_ratio(self):
        """No reports named the drug AND had the event: no ROR is definable."""
        arm = _run(a_named=0)["cohort_scope"]["reported_name_only_analysis"]
        assert "ROR" not in arm
        assert arm["contingency_table"]["a_drug_and_event"] == 0
        assert "greater than zero" in arm["note"]


class TestNoSecondProbeWhenCohortsAgree:
    def test_identical_cohorts_get_a_plain_statement_and_no_arm(self):
        """OZEMPIC, MEFLOQUINE and YELLOW FEVER VACCINE all measure 0.0%.

        These pay for one probe, not two, and must not be given a redundant
        second arm identical to the headline.
        """
        scope = _run(named_total=DRUG_TOTAL_UNION)["cohort_scope"]
        assert scope["reports_matched_by_name_resolution_only"] == 0
        assert "reported_name_only_analysis" not in scope
        assert "percent_matched_by_name_resolution_only" not in scope

    def test_note_is_not_qualified_when_there_is_nothing_to_qualify(self):
        assert "COHORT:" not in _run(named_total=DRUG_TOTAL_UNION)["note"]


class TestImpossibleAndFailedMeasurements:
    def test_a_subset_larger_than_its_cohort_publishes_neither_figure(self):
        """Only openFDA refreshing between the two probes can produce this.

        Publish nothing rather than a figure that cannot be true. The assertion
        is deliberately on the whole serialised result, not just on
        `cohort_scope`: a guard that returns after setting a key would still
        have shipped the impossible number.
        """
        import json

        result = _run(named_total=DRUG_TOTAL_UNION + 1)
        assert result["cohort_scope"] is None
        assert str(DRUG_TOTAL_UNION + 1) not in json.dumps(result)

    def test_a_failed_probe_reads_as_unknown_not_zero(self):
        scope = _run(named_total=None)["cohort_scope"]
        assert scope["reports_naming_queried_drug"] is None
        assert "unknown, not as zero" in scope["note"]

    def test_a_raising_probe_cannot_cost_the_caller_the_analysis(self):
        """The block is additive, so it must not be able to fail the call.

        Without its own guard the enclosing `except Exception` converted any
        error raised while measuring the split into a failed disproportionality
        result, discarding four completed openFDA requests and a correct ROR.
        """
        tool = _tool()

        def fake_count(drug_name=None, adverse_event=None, reported_name_only=False):
            if reported_name_only:
                raise RuntimeError("probe exploded")
            if drug_name and adverse_event:
                return A_UNION
            if drug_name:
                return DRUG_TOTAL_UNION
            if adverse_event:
                return EVENT_TOTAL
            return DB_TOTAL

        with patch.object(tool, "_get_faers_count", side_effect=fake_count):
            result = tool._calculate_disproportionality(
                {"drug_name": "CYANOKIT", "adverse_event": "DEATH"}
            )

        assert result["status"] == "success"
        assert result["metrics"]["ROR"]["value"] == 0.287
        assert result["cohort_scope"] is None


class TestReportedNameClause:
    def test_it_searches_only_the_reported_product_text(self):
        """Not the SPL name fields -- those are what widens the cohort."""
        from tooluniverse.faers_analytics_tool import _faers_search_query

        narrow = _faers_search_query("CYANOKIT", reported_name_only=True)
        assert narrow == 'patient.drug.medicinalproduct:"CYANOKIT"'
        assert "openfda" not in narrow

    def test_the_default_query_is_still_the_union(self):
        from tooluniverse.faers_analytics_tool import _faers_search_query

        wide = _faers_search_query("CYANOKIT")
        assert "patient.drug.openfda.generic_name" in wide
        assert "patient.drug.openfda.brand_name" in wide
