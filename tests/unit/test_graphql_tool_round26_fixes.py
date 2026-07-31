"""Regression guards for two Fix-R26B bugs in graphql_tool.py.

Fix-R26B-1 (empty dict remnants in lists): remove_none_and_empty_values()
stripped a null "disease" key from a list entry like {"disease": None},
turning it into {}, but only filtered list items on their *pre-recursion*
value -- so the resulting {} survived instead of being dropped like every
other null. Confirmed live in OpenTargets_get_associated_drugs_by_target_
ensemblID's "diseases" list (bare {} interleaved with real disease entries
for BRODALUMAB). Fixed by filtering on the recursed result.

Fix-R26B-2 (silent empty result for legacy EFO disease IDs):
OpenTargets_search_gwas_studies_by_disease's studies(diseaseIds: ...) query
returns a normal, non-null {"count": 0} for a stale EFO_* disease id
instead of a null entity, so the existing EFO->MONDO not-found detection
(which only fires on a null entity) never caught it. Confirmed live:
EFO_0000676 (psoriasis) silently returned 0 studies while the current
MONDO_0005083 id returns 79. Fixed by flagging legacy EFO ids specifically
when the studies count comes back 0.
"""

from unittest.mock import patch

import pytest

from tooluniverse.graphql_tool import OpentargetTool, remove_none_and_empty_values

pytestmark = pytest.mark.unit


class TestRemoveNoneAndEmptyValues:
    def test_dict_with_null_key_in_list_is_dropped_not_left_empty(self):
        data = {
            "diseases": [
                {"disease": {"id": "MONDO_1", "name": "psoriasis"}},
                {"disease": None},
                {"disease": {"id": "MONDO_2", "name": "asthma"}},
            ]
        }
        cleaned = remove_none_and_empty_values(data)
        assert cleaned["diseases"] == [
            {"disease": {"id": "MONDO_1", "name": "psoriasis"}},
            {"disease": {"id": "MONDO_2", "name": "asthma"}},
        ]

    def test_plain_none_and_empty_list_still_dropped(self):
        data = {"a": None, "b": [], "c": "keep", "d": [1, None, 2]}
        cleaned = remove_none_and_empty_values(data)
        assert cleaned == {"c": "keep", "d": [1, 2]}


def _tool(name="OpenTargets_get_associated_diseases_by_target_ensemblID"):
    tool = OpentargetTool.__new__(OpentargetTool)
    tool.endpoint_url = "https://api.platform.opentargets.org/api/v4/graphql"
    tool.query_schema = "query searchStudies($diseaseIds: [String!]) { studies { count } }"
    tool.tool_config = {"name": name}
    return tool


class TestLegacyEfoStudiesNote:
    def test_legacy_efo_id_with_zero_studies_gets_note(self):
        tool = _tool()
        with patch(
            "tooluniverse.graphql_tool.GraphQLTool.run",
            return_value={"status": "success", "data": {"studies": {"count": 0}}},
        ):
            result = tool.run({"diseaseIds": ["EFO_0000676"]})

        assert result["status"] == "success"
        assert "EFO to MONDO" in result["metadata"]["note"]

    def test_current_mondo_id_with_results_gets_no_note(self):
        tool = _tool()
        with patch(
            "tooluniverse.graphql_tool.GraphQLTool.run",
            return_value={"status": "success", "data": {"studies": {"count": 79}}},
        ):
            result = tool.run({"diseaseIds": ["MONDO_0005083"]})

        assert "metadata" not in result or "note" not in result.get("metadata", {})

    def test_mondo_id_with_zero_studies_gets_no_note(self):
        # A genuine current MONDO id with zero studies is a real answer,
        # not a stale-id symptom -- only EFO_-prefixed ids should get the note.
        tool = _tool()
        with patch(
            "tooluniverse.graphql_tool.GraphQLTool.run",
            return_value={"status": "success", "data": {"studies": {"count": 0}}},
        ):
            result = tool.run({"diseaseIds": ["MONDO_9999999"]})

        assert "metadata" not in result or "note" not in result.get("metadata", {})


class TestIntOGenNoteNotMisattributed:
    """Regression guard for Fix-R31D-3: the IntOGen "0 evidence rows" note
    (Feature-122B-002, above) was applied to EVERY OpentargetTool-based tool
    whenever evidences.count == 0, not just the actual IntOGen-only tool
    (OpenTargets_target_disease_evidence). Confirmed live: querying
    OpenTargets_get_evidence_by_datasource with datasourceIds=["chembl"]
    (a datasource IntOGen never touches) got the note blaming IntOGen for
    the zero count -- even telling the caller to "use
    OpenTargets_get_evidence_by_datasource instead" while that IS the tool
    being called."""

    def _zero_evidence_result(self):
        return {
            "status": "success",
            "data": {"disease": {"id": "MONDO_0005233", "evidences": {"count": 0}}},
        }

    def test_note_fires_for_the_real_intogen_tool(self):
        tool = _tool(name="OpenTargets_target_disease_evidence")
        with patch(
            "tooluniverse.graphql_tool.GraphQLTool.run",
            return_value=self._zero_evidence_result(),
        ):
            result = tool.run({"efoId": "EFO_0001360"})

        assert "IntOGen" in result["metadata"]["note"]

    def test_note_does_not_fire_for_other_evidence_tools(self):
        tool = _tool(name="OpenTargets_get_evidence_by_datasource")
        with patch(
            "tooluniverse.graphql_tool.GraphQLTool.run",
            return_value=self._zero_evidence_result(),
        ):
            result = tool.run({"efoId": "MONDO_0005233", "datasourceIds": ["chembl"]})

        assert "metadata" not in result or "note" not in result.get("metadata", {})
