#!/usr/bin/env python3
"""Unit tests for ontology-mapping-services depth tools.

Covers the two cross-reference / cross-registry mapping tools added to existing
tool classes (no new @register_tool class):

- ``ols_get_term_xrefs``           -> OLSTool.get_term_xrefs operation
- ``Bioregistry_get_prefix_mappings`` -> BioregistryTool.get_prefix_mappings operation

Each tool is tested for the parse (success) path and the error path using
mocked HTTP so the suite is deterministic and offline.
"""

from unittest.mock import Mock, patch

import pytest

from tooluniverse.ols_tool import OLSTool
from tooluniverse.bioregistry_tool import BioregistryTool


# ---------------------------------------------------------------------------
# ols_get_term_xrefs (OLSTool, operation=get_term_xrefs)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestOLSGetTermXrefs:
    def setup_method(self):
        self.tool = OLSTool({"name": "test_ols"})

    # The OLS4 ontology-scoped /terms response shape carrying obo_xref.
    _EFO_RESPONSE = {
        "_embedded": {
            "terms": [
                {
                    "obo_id": "EFO:0004611",
                    "iri": "http://www.ebi.ac.uk/efo/EFO_0004611",
                    "label": "low density lipoprotein cholesterol measurement",
                    "ontology_name": "efo",
                    "is_obsolete": False,
                    "obo_xref": [
                        {
                            "database": "NCIt",
                            "id": "C105588",
                            "description": None,
                            "url": "http://purl.obolibrary.org/obo/NCIT_C105588",
                        },
                        {
                            "database": "SNOMEDCT",
                            "id": "113079009",
                            "description": None,
                            "url": "http://purl.bioontology.org/ontology/SNOMEDCT/113079009",
                        },
                    ],
                }
            ]
        }
    }

    @patch.object(OLSTool, "_get_json")
    def test_get_term_xrefs_success(self, mock_get_json):
        """Parse path: obo_xref array becomes normalized xrefs with CURIEs."""
        mock_get_json.return_value = self._EFO_RESPONSE

        result = self.tool.run({"operation": "get_term_xrefs", "id": "EFO:0004611"})

        assert result["status"] == "success"
        data = result["data"]
        assert data["obo_id"] == "EFO:0004611"
        assert data["label"].startswith("low density lipoprotein")
        assert data["ontology_name"] == "efo"
        assert result["metadata"]["xref_count"] == 2
        assert result["metadata"]["ontology"] == "efo"

        curies = {x["curie"] for x in data["xrefs"]}
        assert "NCIt:C105588" in curies
        assert "SNOMEDCT:113079009" in curies
        # Each normalized xref exposes the resolver URL.
        ncit = next(x for x in data["xrefs"] if x["database"] == "NCIt")
        assert ncit["id"] == "C105588"
        assert ncit["url"].endswith("NCIT_C105588")

    @patch.object(OLSTool, "_get_json")
    def test_get_term_xrefs_ontology_inferred_from_curie(self, mock_get_json):
        """Ontology is auto-inferred from the CURIE prefix (mondo)."""
        mock_get_json.return_value = {
            "_embedded": {
                "terms": [
                    {
                        "obo_id": "MONDO:0005148",
                        "iri": "http://purl.obolibrary.org/obo/MONDO_0005148",
                        "label": "type 2 diabetes mellitus",
                        "ontology_name": "mondo",
                        "obo_xref": [
                            {
                                "database": "DOID",
                                "id": "9352",
                                "description": "MONDO:equivalentTo",
                                "url": "http://purl.obolibrary.org/obo/DOID_9352",
                            }
                        ],
                    }
                ]
            }
        }

        result = self.tool.run(
            {"operation": "get_term_xrefs", "term_id": "MONDO:0005148"}
        )

        assert result["status"] == "success"
        # First call should hit the mondo-scoped endpoint with obo_id param.
        first_call = mock_get_json.call_args_list[0]
        assert "/api/ontologies/mondo/terms" in first_call.args[0]
        assert first_call.kwargs["params"]["obo_id"] == "MONDO:0005148"
        assert result["data"]["xrefs"][0]["curie"] == "DOID:9352"

    def test_get_term_xrefs_missing_id(self):
        """Error path: no identifier supplied."""
        result = self.tool.run({"operation": "get_term_xrefs"})
        assert result["status"] == "error"
        assert "id" in result["error"]

    @patch.object(OLSTool, "_get_json")
    def test_get_term_xrefs_term_not_found(self, mock_get_json):
        """Error path: OLS returns no terms for the identifier."""
        mock_get_json.return_value = {"_embedded": {"terms": []}}
        result = self.tool.run({"operation": "get_term_xrefs", "id": "EFO:9999999"})
        assert result["status"] == "error"
        assert "not found" in result["error"].lower()


# ---------------------------------------------------------------------------
# Bioregistry_get_prefix_mappings (BioregistryTool, operation=get_prefix_mappings)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBioregistryGetPrefixMappings:
    def setup_method(self):
        self.tool = BioregistryTool({"name": "test_bioregistry"})

    @patch("tooluniverse.bioregistry_tool.requests.get")
    def test_get_prefix_mappings_success(self, mock_get):
        """Parse path: the 'mappings' object is surfaced with metadata."""
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "prefix": "chebi",
            "name": "Chemical Entities of Biological Interest",
            "mappings": {
                "obofoundry": "chebi",
                "miriam": "chebi",
                "ols": "chebi",
                "n2t": "chebi",
                "bioportal": "CHEBI",
                "fairsharing": "FAIRsharing.62qk8w",
            },
        }
        mock_get.return_value = mock_resp

        result = self.tool.run({"operation": "get_prefix_mappings", "prefix": "chebi"})

        assert result["status"] == "success"
        data = result["data"]
        assert data["prefix"] == "chebi"
        mappings = data["mappings"]
        assert mappings["obofoundry"] == "chebi"
        assert mappings["fairsharing"] == "FAIRsharing.62qk8w"
        assert result["metadata"]["mapping_count"] == 6
        assert "obofoundry" in result["metadata"]["registries"]
        # registries list is sorted
        assert result["metadata"]["registries"] == sorted(
            result["metadata"]["registries"]
        )

    @patch("tooluniverse.bioregistry_tool.requests.get")
    def test_get_prefix_mappings_no_mappings_field(self, mock_get):
        """Graceful handling when the record omits 'mappings'."""
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"prefix": "obscure", "name": "Obscure"}
        mock_get.return_value = mock_resp

        result = self.tool.run(
            {"operation": "get_prefix_mappings", "prefix": "obscure"}
        )
        assert result["status"] == "success"
        assert result["data"]["mappings"] == {}
        assert result["metadata"]["mapping_count"] == 0

    def test_get_prefix_mappings_missing_prefix(self):
        """Error path: no prefix supplied."""
        result = self.tool.run({"operation": "get_prefix_mappings"})
        assert result["status"] == "error"
        assert "prefix" in result["error"].lower()

    @patch("tooluniverse.bioregistry_tool.requests.get")
    def test_get_prefix_mappings_not_found(self, mock_get):
        """Error path: unknown prefix -> HTTP 404."""
        mock_resp = Mock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp

        result = self.tool.run(
            {"operation": "get_prefix_mappings", "prefix": "nopenope"}
        )
        assert result["status"] == "error"
        assert "not found" in result["error"].lower()

    @patch("tooluniverse.bioregistry_tool.requests.get")
    def test_get_prefix_mappings_network_error(self, mock_get):
        """Error path: requests raises -> caught, never propagates."""
        mock_get.side_effect = Exception("connection reset")
        result = self.tool.run({"operation": "get_prefix_mappings", "prefix": "chebi"})
        assert result["status"] == "error"
        assert "connection reset" in result["error"]
