"""Regression guard for metabolite_tool.py's `_ctd_diseases`.

Originally backed by the RENCI Automat CTD mirror (used as a fallback after
CTD's native batchQuery.go became CAPTCHA-blocked), and now backed by
mydisease.info after that mirror was fully decommissioned (its registry no
longer lists a 'ctd' backend at all -- see ctd_tool.py for the full
history). mydisease.info's cached CTD data DOES carry a genuine
`direct_evidence` field (unlike RENCI's edges, which never had one), and its
`pubmed` field is sometimes a single string and sometimes a list of several
PMIDs -- both shapes must be read into `PubMedIDs` without crashing.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.metabolite_tool import MetaboliteTool

pytestmark = pytest.mark.unit


def _tool():
    return MetaboliteTool({"name": "metabolite_test", "fields": {}})


def _query_resp(hits):
    r = MagicMock()
    r.raise_for_status = MagicMock()
    r.json.return_value = {"hits": hits}
    return r


def _ols_resp(label):
    r = MagicMock()
    r.raise_for_status = MagicMock()
    r.json.return_value = {"_embedded": {"terms": [{"label": label}]}}
    return r


def _mesh_resp(label):
    r = MagicMock()
    r.raise_for_status = MagicMock()
    r.json.return_value = {"terms": [{"label": label, "preferred": True}]}
    return r


class TestCtdDiseasesPubmedExtraction:
    def test_publications_extracted_for_matching_chemical(self):
        tool = _tool()
        hits = [
            {
                "_id": "MONDO:0013209",
                "mondo": {"label": "metabolic dysfunction-associated steatotic liver disease"},
                "ctd": {
                    "chemical_related_to_disease": [
                        {
                            "chemical_name": "cholesterol",
                            "mesh_chemical_id": "D002784",
                            "direct_evidence": "marker/mechanism",
                            "pubmed": ["29486218", "20557099"],
                        }
                    ]
                },
            }
        ]
        with patch(
            "tooluniverse.metabolite_tool.requests.get",
            return_value=_query_resp(hits),
        ):
            rows = tool._ctd_diseases("cholesterol")

        assert len(rows) == 1
        assert rows[0]["PubMedIDs"] == ["29486218", "20557099"]
        assert rows[0]["DirectEvidence"] == "marker/mechanism"
        assert rows[0]["DiseaseName"] == "metabolic dysfunction-associated steatotic liver disease"

    def test_single_pubmed_string_becomes_single_item_list(self):
        tool = _tool()
        hits = [
            {
                "_id": "MONDO:0000001",
                "mondo": {"label": "some disease"},
                "ctd": {
                    "chemical_related_to_disease": {
                        "chemical_name": "cholesterol",
                        "pubmed": "12345",
                    }
                },
            }
        ]
        with patch(
            "tooluniverse.metabolite_tool.requests.get",
            return_value=_query_resp(hits),
        ):
            rows = tool._ctd_diseases("cholesterol")

        assert rows[0]["PubMedIDs"] == ["12345"]

    def test_missing_mydisease_label_is_resolved_by_exact_ols_id(self):
        tool = _tool()
        hits = [
            {
                "_id": "EFO:0009426",
                "ctd": {
                    "chemical_related_to_disease": {
                        "chemical_name": "cholesterol",
                        "pubmed": "20484746",
                    }
                },
            }
        ]
        with patch(
            "tooluniverse.metabolite_tool.requests.get",
            side_effect=[_query_resp(hits), _ols_resp("necrosis")],
        ):
            rows = tool._ctd_diseases("cholesterol")

        assert rows[0]["DiseaseName"] == "necrosis"
        assert rows[0]["DiseaseNameSource"] == "EBI OLS (efo)"

    def test_umls_hit_uses_its_mesh_cross_reference_for_name(self):
        tool = _tool()
        hits = [
            {
                "_id": "UMLS:C0025261",
                "umls": {"mesh": {"preferred": "D008569"}},
                "ctd": {
                    "chemical_related_to_disease": {
                        "chemical_name": "cholesterol",
                    }
                },
            }
        ]
        with patch(
            "tooluniverse.metabolite_tool.requests.get",
            side_effect=[_query_resp(hits), _mesh_resp("Memory Disorders")],
        ):
            rows = tool._ctd_diseases("cholesterol")

        assert rows[0]["DiseaseName"] == "Memory Disorders"
        assert rows[0]["DiseaseNameSource"] == "NLM MeSH"

    def test_list_merged_umls_cross_reference_is_supported(self):
        tool = _tool()
        hits = [
            {
                "_id": "UMLS:C0025261",
                "umls": [{"mesh": {"preferred": "D008569"}}],
                "ctd": {
                    "chemical_related_to_disease": {
                        "chemical_name": "cholesterol",
                    }
                },
            }
        ]
        with patch(
            "tooluniverse.metabolite_tool.requests.get",
            side_effect=[_query_resp(hits), _mesh_resp("Memory Disorders")],
        ):
            rows = tool._ctd_diseases("cholesterol")

        assert rows[0]["DiseaseName"] == "Memory Disorders"

    def test_entry_with_no_publications_gets_empty_list_not_crash(self):
        tool = _tool()
        hits = [
            {
                "_id": "MONDO:0000001",
                "mondo": {"label": "some disease"},
                "ctd": {
                    "chemical_related_to_disease": [
                        {"chemical_name": "cholesterol", "direct_evidence": None}
                    ]
                },
            }
        ]
        with patch(
            "tooluniverse.metabolite_tool.requests.get",
            return_value=_query_resp(hits),
        ):
            rows = tool._ctd_diseases("cholesterol")

        assert rows[0]["PubMedIDs"] == []

    def test_non_matching_chemical_name_is_filtered_out(self):
        # A hit's chemical_related_to_disease array can list many unrelated
        # chemicals for the same disease -- only entries whose own name
        # matches the query term should turn into rows.
        tool = _tool()
        hits = [
            {
                "_id": "MONDO:0000001",
                "mondo": {"label": "some disease"},
                "ctd": {
                    "chemical_related_to_disease": [
                        {"chemical_name": "aspirin", "pubmed": "111"},
                        {"chemical_name": "cholesterol", "pubmed": "222"},
                    ]
                },
            }
        ]
        with patch(
            "tooluniverse.metabolite_tool.requests.get",
            return_value=_query_resp(hits),
        ):
            rows = tool._ctd_diseases("cholesterol")

        assert len(rows) == 1
        assert rows[0]["PubMedIDs"] == ["222"]

    def test_merged_ctd_list_document_is_flattened(self):
        # BioThings occasionally merges more than one source record onto the
        # same disease document, in which case `ctd` is a list of
        # sub-documents instead of a single dict -- confirmed live for at
        # least one MONDO document.
        tool = _tool()
        hits = [
            {
                "_id": "MONDO:0002525",
                "mondo": {"label": "inherited lipid metabolism disorder"},
                "ctd": [
                    {
                        "chemical_related_to_disease": [
                            {"chemical_name": "cholesterol", "pubmed": "333"}
                        ]
                    }
                ],
            }
        ]
        with patch(
            "tooluniverse.metabolite_tool.requests.get",
            return_value=_query_resp(hits),
        ):
            rows = tool._ctd_diseases("cholesterol")

        assert len(rows) == 1
        assert rows[0]["PubMedIDs"] == ["333"]


class TestGetDiseasesPubmedIdsFormat:
    def test_list_format_pubmed_ids_passed_through(self):
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
