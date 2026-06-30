"""
Unit tests for OpenTargets EFO->MONDO migration handling (issue #264).

OpenTargets migrated most disease IDs from EFO to MONDO. A legacy EFO disease
ID now resolves to ``{"data": {"disease": null}}``, which
``remove_none_and_empty_values()`` strips to ``{"data": {}}``. These tests pin
the behaviour that an unresolved disease ID is reported as an explicit error
rather than a misleading empty success (OpentargetTool) or a KeyError crash
(DiseaseTargetScoreTool).
"""

import json
from unittest.mock import patch

import pytest


def _load(path, name):
    with open(path) as f:
        return next(t for t in json.load(f) if t["name"] == name)


class TestRemoveNoneStripsNullEntity:
    def test_null_disease_is_stripped_to_empty(self):
        from tooluniverse.graphql_tool import remove_none_and_empty_values

        cleaned = remove_none_and_empty_values({"data": {"disease": None}})
        # The null entity disappears, leaving an empty data object -- this is the
        # root cause the tools must defend against.
        assert cleaned == {"data": {}}


class TestEntityNotFoundMessage:
    def test_disease_id_message_mentions_mondo(self):
        from tooluniverse.graphql_tool import _ot_entity_not_found_message

        msg = _ot_entity_not_found_message({"efoId": "EFO_0000537"})
        assert "EFO_0000537" in msg
        assert "MONDO" in msg

    def test_diseaseids_list_is_reported(self):
        from tooluniverse.graphql_tool import _ot_entity_not_found_message

        msg = _ot_entity_not_found_message({"diseaseIds": ["EFO_0000384"]})
        assert "EFO_0000384" in msg

    def test_ensembl_id_message(self):
        from tooluniverse.graphql_tool import _ot_entity_not_found_message

        msg = _ot_entity_not_found_message({"ensemblId": "ENSG00000000000"})
        assert "ENSG00000000000" in msg
        assert "gene_symbol" in msg


class TestOpentargetToolUnresolvedDisease:
    @pytest.fixture
    def tool(self):
        from tooluniverse.graphql_tool import OpentargetTool

        cfg = _load(
            "src/tooluniverse/data/opentarget_tools.json",
            "OpenTargets_get_associated_targets_by_disease_efoId",
        )
        return OpentargetTool(cfg)

    def test_unresolved_efo_id_returns_error_not_empty_success(self, tool):
        # API returns the post-strip empty payload for a stale EFO disease ID.
        with patch(
            "tooluniverse.graphql_tool.execute_query",
            return_value={"data": {}},
        ):
            result = tool.run({"efoId": "EFO_0000537"})
        assert result["status"] == "error"
        assert "EFO_0000537" in result["error"]

    def test_resolved_disease_returns_success(self, tool):
        payload = {
            "data": {
                "disease": {
                    "id": "MONDO_0005011",
                    "name": "Crohn disease",
                    "associatedTargets": {"count": 1},
                }
            }
        }
        with patch("tooluniverse.graphql_tool.execute_query", return_value=payload):
            result = tool.run({"efoId": "MONDO_0005011"})
        assert result["status"] == "success"
        assert result["data"]["disease"]["id"] == "MONDO_0005011"


class TestDiseaseTargetScoreToolUnresolvedDisease:
    @pytest.fixture
    def tool(self):
        from tooluniverse.graphql_tool import DiseaseTargetScoreTool

        cfg = _load(
            "src/tooluniverse/data/disease_target_score_tools.json",
            "chembl_disease_target_score",
        )
        return DiseaseTargetScoreTool(cfg)

    def test_unresolved_efo_id_returns_error_not_keyerror(self, tool):
        # Stripped payload has no "disease" key -- the old code did
        # response_data["data"]["disease"] and raised KeyError.
        with patch(
            "tooluniverse.graphql_tool.execute_query",
            return_value={"data": {}},
        ):
            result = tool.run({"efoId": "EFO_0000339", "pageSize": 5})
        assert result["status"] == "error"
        assert "EFO_0000339" in result["error"]

    def test_resolved_disease_returns_success(self, tool):
        payload = {
            "data": {
                "disease": {
                    "id": "MONDO_0011996",
                    "name": "chronic myelogenous leukemia, BCR-ABL1 positive",
                    "associatedTargets": {
                        "count": 1,
                        "rows": [
                            {
                                "target": {
                                    "approvedSymbol": "ABL1",
                                    "id": "ENSG00000097007",
                                },
                                "datasourceScores": [
                                    {"id": "clinical_precedence", "score": 0.99}
                                ],
                            }
                        ],
                    },
                }
            }
        }
        with patch("tooluniverse.graphql_tool.execute_query", return_value=payload):
            result = tool.run(
                {
                    "efoId": "MONDO_0011996",
                    "datasourceId": "clinical_precedence",
                    "pageSize": 5,
                }
            )
        assert result["status"] == "success"
        assert result["data"]["total_targets_with_scores"] == 1
        assert result["data"]["target_scores"][0]["target_symbol"] == "ABL1"
