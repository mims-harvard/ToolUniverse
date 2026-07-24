"""Regression guard for Fix-R27D-1 in metabolite_tool.py's `_ctd_diseases`
(the RENCI Automat CTD-mirror fallback used since CTD's native
batchQuery.go became CAPTCHA-blocked).

Confirmed live (automat.renci.org/ctd chemical-disease edges for
cholesterol/CHEBI:16113): edge_props only ever carries agent_type/
knowledge_level/primary_knowledge_source/publications -- there is no
predicate/qualified_predicate field, so `direct_evidence` is genuinely
unavailable from this source (not a bug to "fix" further, now documented
honestly). `publications` (PMID:xxxxx strings) IS present but was
previously hardcoded to an empty list instead of being read, so
`pubmed_ids` came back [] for every single result (100% of associations
for both cholesterol and lutein in the original report).
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.metabolite_tool import MetaboliteTool

pytestmark = pytest.mark.unit


def _tool():
    return MetaboliteTool({"name": "metabolite_test", "fields": {}})


def _cypher_resp(curie):
    r = MagicMock()
    r.raise_for_status = MagicMock()
    r.json.return_value = {"results": [{"data": [{"row": [curie]}]}]}
    return r


def _edges_resp(edges):
    r = MagicMock()
    r.raise_for_status = MagicMock()
    r.json.return_value = edges
    return r


class TestCtdDiseasesPubmedExtraction:
    def test_publications_extracted_and_pmid_prefix_stripped(self):
        tool = _tool()
        edges = [
            [
                {"name": "cholesterol", "id": "CHEBI:16113"},
                {
                    "agent_type": "manual_agent",
                    "knowledge_level": "knowledge_assertion",
                    "primary_knowledge_source": "infores:ctd",
                    "publications": ["PMID:29486218", "PMID:20557099"],
                },
                {
                    "name": "metabolic dysfunction-associated steatotic liver disease",
                    "id": "MONDO:0013209",
                },
            ]
        ]
        with patch(
            "tooluniverse.metabolite_tool.requests.post",
            return_value=_cypher_resp("CHEBI:16113"),
        ), patch(
            "tooluniverse.metabolite_tool.requests.get",
            return_value=_edges_resp(edges),
        ):
            rows = tool._ctd_diseases("cholesterol")

        assert len(rows) == 1
        assert rows[0]["PubMedIDs"] == ["29486218", "20557099"]
        assert rows[0]["DirectEvidence"] is None

    def test_edge_with_no_publications_gets_empty_list_not_crash(self):
        tool = _tool()
        edges = [
            [
                {"name": "cholesterol", "id": "CHEBI:16113"},
                {"agent_type": "manual_agent"},
                {"name": "some disease", "id": "MONDO:0000001"},
            ]
        ]
        with patch(
            "tooluniverse.metabolite_tool.requests.post",
            return_value=_cypher_resp("CHEBI:16113"),
        ), patch(
            "tooluniverse.metabolite_tool.requests.get",
            return_value=_edges_resp(edges),
        ):
            rows = tool._ctd_diseases("cholesterol")

        assert rows[0]["PubMedIDs"] == []


class TestGetDiseasesPubmedIdsFormat:
    def test_list_format_pubmed_ids_passed_through(self):
        # PubMedIDs is now always a list (from _ctd_diseases), not the
        # legacy pipe-delimited string -- both shapes must work.
        tool = _tool()
        with patch.object(
            tool,
            "_resolve_ctd_term",
            return_value=(
                "cholesterol",
                [
                    {
                        "DiseaseName": "atherosclerosis",
                        "DiseaseID": "MONDO:0005311",
                        "DirectEvidence": None,
                        "PubMedIDs": ["111", "222"],
                    }
                ],
            ),
        ), patch.object(
            tool, "_get_properties", return_value={"Title": "cholesterol"}
        ), patch.object(
            tool, "_get_synonyms", return_value=[]
        ), patch.object(
            tool, "_resolve_to_cid", return_value=5997
        ):
            result = tool._get_diseases({"compound_name": "cholesterol"})

        assert result["data"]["diseases"][0]["pubmed_ids"] == ["111", "222"]

    def test_legacy_pipe_string_format_still_works(self):
        tool = _tool()
        with patch.object(
            tool,
            "_resolve_ctd_term",
            return_value=(
                "cholesterol",
                [
                    {
                        "DiseaseName": "atherosclerosis",
                        "DiseaseID": "MONDO:0005311",
                        "DirectEvidence": "marker/mechanism",
                        "PubMedIDs": "111|222",
                    }
                ],
            ),
        ), patch.object(
            tool, "_get_properties", return_value={"Title": "cholesterol"}
        ), patch.object(
            tool, "_get_synonyms", return_value=[]
        ), patch.object(
            tool, "_resolve_to_cid", return_value=5997
        ):
            result = tool._get_diseases({"compound_name": "cholesterol"})

        assert result["data"]["diseases"][0]["pubmed_ids"] == ["111", "222"]
