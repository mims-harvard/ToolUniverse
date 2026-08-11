"""
Compose tools must not report success when a step could not run.

Covers three success-shaped failures:
  * a ComposeTool that keeps going with an unloadable dependency and says nothing
  * LiteratureSearchTool returning the sub-call's error string as its own result
  * DrugSafetyAnalyzer summarising raw upstream shapes that the tool never emits,
    so populated sources are reported as absent

Fully offline: every tool call is a stub.
"""

from types import SimpleNamespace

import pytest

from tooluniverse.compose_scripts import drug_safety_analyzer, literature_tool, payload
from tooluniverse.compose_tool import ComposeTool


@pytest.mark.parametrize(
    "result,missing,expected",
    [
        # Recorded on a dict result, without disturbing existing fields.
        ({"a": 1}, {"MissingAgent"}, {"a": 1, "missing_tools": ["MissingAgent"]}),
        # Nothing missing: the payload is left exactly as the composition built it.
        ({"a": 1}, set(), {"a": 1}),
        # A value the composition set itself wins over the framework's.
        (
            {"missing_tools": ["Explicit"]},
            {"Framework"},
            {"missing_tools": ["Explicit"]},
        ),
        # _call_tool returns a bare string precisely when a tool was unavailable,
        # so that result must be wrapped rather than lose the annotation.
        ("text", {"Missing"}, {"result": "text", "missing_tools": ["Missing"]}),
    ],
    ids=["dict", "nothing-missing", "composition-wins", "string-wrapped"],
)
def test_missing_tools_annotation(result, missing, expected):
    """The degradation the framework already computes must reach the payload."""
    assert ComposeTool._annotate_missing_tools(result, missing) == expected


def test_missing_tool_is_recorded_at_call_time():
    """
    Dependency discovery is a regex over literal tool names, so a tool invoked
    through a variable is invisible to the pre-flight check. Recording the miss
    inside _call_tool is what makes the annotation cover every compose script.
    """
    universe = SimpleNamespace(callable_functions={}, all_tool_dict={})
    tool = ComposeTool(
        {
            "name": "T",
            "type": "ComposeTool",
            "auto_load_dependencies": False,
            "required_tools": [],
        },
        tooluniverse=universe,
    )
    tool._missing_during_run = set()

    result = tool._call_tool("NoSuchTool", {})

    assert "not found in loaded tools" in result
    assert tool._missing_during_run == {"NoSuchTool"}


class TestLiteratureSearchDegradation:
    """An unavailable summariser must be an error, not a success-shaped string."""

    @staticmethod
    def _call_tool(name, _args):
        return {"status": "success", "data": [f"{name}-record"]}

    def test_missing_reviewer_reports_failure_and_keeps_literature(self):
        universe = SimpleNamespace(all_tool_dict={})

        result = literature_tool.compose(
            {"research_topic": "wound healing"}, universe, self._call_tool
        )

        assert isinstance(result, dict), "must not return a bare error string"
        assert result["success"] is False
        assert "MedicalLiteratureReviewer" in result["error"]
        # The three retrieved sources used to be discarded entirely.
        assert set(result["literature"]) == {"pmc", "openalex", "pubtator"}

    def test_available_reviewer_result_is_returned_unchanged(self):
        universe = SimpleNamespace(all_tool_dict={"MedicalLiteratureReviewer": {}})
        sentinel = {"success": True, "result": "a real review"}

        def call_tool(name, _args):
            if name == "MedicalLiteratureReviewer":
                return sentinel
            return {"status": "success", "data": []}

        result = literature_tool.compose(
            {"research_topic": "wound healing"}, universe, call_tool
        )
        assert result is sentinel


class TestEnvelopePayload:
    """Envelope-wrapped responses must not be counted as missing data."""

    def test_unwraps_successful_envelope(self):
        assert payload({"status": "success", "data": [1, 2]}) == [1, 2]

    def test_returns_none_for_failed_call(self):
        """A failed source must not be indistinguishable from an empty one."""
        assert payload({"status": "error", "data": []}) is None

    def test_passes_through_unwrapped_response(self):
        assert payload({"IdentifierList": {}}) == {"IdentifierList": {}}


class TestDrugSafetyAnalyzerSummary:
    def test_summary_matches_the_data_in_the_same_response(self):
        articles = [{"id": n} for n in range(10)]

        def call_tool(name, _args):
            if name == "FAERS_count_reactions_by_drug_event":
                return {"status": "success", "data": {"results": [{"term": "SEIZURE"}]}}
            if name == "PubChem_get_CID_by_compound_name":
                return {
                    "status": "success",
                    "data": {"IdentifierList": {"CID": [3373]}},
                }
            if name == "PubChem_get_compound_properties_by_CID":
                return {"status": "success", "data": {"PropertyTable": {}}}
            if name == "EuropePMC_search_articles":
                return {"status": "success", "data": articles}
            raise AssertionError(f"unexpected tool {name}")

        result = drug_safety_analyzer.compose(
            {"drug_name": "flumazenil"}, SimpleNamespace(), call_tool
        )

        summary = result["analysis_summary"]
        assert summary["literature_papers_found"] == len(articles)
        assert summary["has_molecular_data"] is True
        assert summary["has_adverse_events"] is True
