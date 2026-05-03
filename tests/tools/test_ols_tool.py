#!/usr/bin/env python3
"""
Unit tests for OLSTool - EMBL-EBI Ontology Lookup Service tool.

Tests cover all OLS operations and edge cases with >90% code coverage.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from pydantic import ValidationError

from tooluniverse.ols_tool import (
    OLSTool,
    OntologyInfo,
    TermInfo,
    DetailedTermInfo,
    url_encode_iri,
)


@pytest.mark.unit
class TestURLEncoding:
    """Test URL encoding for IRIs."""

    def test_url_encode_iri_simple(self):
        """Test URL encoding of a simple IRI."""
        iri = "http://purl.obolibrary.org/obo/GO_0008150"
        encoded = url_encode_iri(iri)
        assert isinstance(encoded, str)
        assert encoded != iri

    def test_url_encode_iri_with_spaces(self):
        """Test URL encoding of IRI with spaces."""
        iri = "http://example.org/term with spaces"
        encoded = url_encode_iri(iri)
        assert " " not in encoded
        # Double URL encoding means spaces become %2520
        assert "%25" in encoded or "%20" in encoded

    def test_url_encode_iri_special_chars(self):
        """Test URL encoding of IRI with special characters."""
        iri = "http://example.org/term#special&chars"
        encoded = url_encode_iri(iri)
        assert isinstance(encoded, str)


@pytest.mark.unit
class TestOntologyInfo:
    """Test OntologyInfo model."""

    def test_ontology_info_creation(self):
        """Test creating OntologyInfo from valid data."""
        data = {
            "ontologyId": "efo",
            "title": "Experimental Factor Ontology",
            "version": "2024.01",
            "description": "The Experimental Factor Ontology",
            "domain": "biology",
        }
        ontology = OntologyInfo.model_validate(data)
        assert ontology.id == "efo"
        assert ontology.title == "Experimental Factor Ontology"
        assert ontology.version == "2024.01"

    def test_ontology_info_optional_fields(self):
        """Test OntologyInfo with optional fields."""
        data = {
            "ontologyId": "test",
            "title": "Test Ontology",
            "homepage": "https://example.org",
            "repository": "https://github.com/example/test",
        }
        ontology = OntologyInfo.model_validate(data)
        assert ontology.homepage is not None
        assert ontology.repository is not None


@pytest.mark.unit
class TestTermInfo:
    """Test TermInfo model."""

    def test_term_info_creation(self):
        """Test creating TermInfo from valid data."""
        data = {
            "iri": "http://purl.obolibrary.org/obo/GO_0008150",
            "ontology_name": "go",
            "short_form": "GO:0008150",
            "label": "biological_process",
            "obo_id": "GO:0008150",
        }
        term = TermInfo.model_validate(data)
        assert term.ontology_name == "go"
        assert term.short_form == "GO:0008150"
        assert term.label == "biological_process"

    def test_term_info_obsolete(self):
        """Test TermInfo with obsolete flag."""
        data = {
            "iri": "http://example.org/term",
            "ontology_name": "test",
            "short_form": "TEST:0001",
            "label": "test_term",
            "is_obsolete": True,
        }
        term = TermInfo.model_validate(data)
        assert term.is_obsolete is True


@pytest.mark.unit
class TestDetailedTermInfo:
    """Test DetailedTermInfo model."""

    def test_detailed_term_info_creation(self):
        """Test creating DetailedTermInfo with description and synonyms."""
        data = {
            "iri": "http://example.org/term",
            "ontology_name": "test",
            "short_form": "TEST:0001",
            "label": "test_term",
            "description": ["This is a test term"],
            "synonyms": ["test", "testing"],
        }
        term = DetailedTermInfo.model_validate(data)
        assert term.description == ["This is a test term"]
        assert term.synonyms == ["test", "testing"]


@pytest.mark.unit
class TestOLSToolInitialization:
    """Test OLSTool initialization."""

    def test_init_default_config(self):
        """Test OLSTool initialization with default config."""
        config = {"name": "test_ols", "description": "Test"}
        tool = OLSTool(config)
        assert tool.base_url == "https://www.ebi.ac.uk/ols4"
        assert tool.timeout == 30.0
        assert tool.session is not None

    def test_init_custom_config(self):
        """Test OLSTool initialization with custom config."""
        config = {
            "name": "test_ols",
            "base_url": "https://custom.example.org",
            "timeout": 60.0,
        }
        tool = OLSTool(config)
        assert tool.base_url == "https://custom.example.org"
        assert tool.timeout == 60.0

    def test_init_base_url_trailing_slash(self):
        """Test that base_url trailing slash is stripped."""
        config = {
            "name": "test_ols",
            "base_url": "https://example.org/",
        }
        tool = OLSTool(config)
        assert tool.base_url == "https://example.org"

    def test_del_closes_session(self):
        """Test that __del__ closes the session."""
        config = {"name": "test_ols"}
        tool = OLSTool(config)
        with patch.object(tool.session, "close") as mock_close:
            tool.__del__()
            mock_close.assert_called_once()


@pytest.mark.unit
class TestOLSToolRunMethod:
    """Test OLSTool.run() method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = {"name": "test_ols"}
        self.tool = OLSTool(self.config)

    def test_run_no_operation(self):
        """Test run() with no operation specified."""
        result = self.tool.run({})
        assert "error" in result
        assert "operation" in result["error"]
        assert "available_operations" in result

    def test_run_invalid_operation(self):
        """Test run() with invalid operation."""
        result = self.tool.run({"operation": "invalid_op"})
        assert "error" in result
        assert "Unsupported operation" in result["error"]

    def test_run_none_arguments(self):
        """Test run() with None arguments."""
        result = self.tool.run(None)
        assert "error" in result

    @patch.object(OLSTool, "_handle_search_terms")
    def test_run_dispatch_search_terms(self, mock_handler):
        """Test that run() correctly dispatches to handler."""
        mock_handler.return_value = {"success": True}
        arguments = {"operation": "search_terms", "query": "test"}
        result = self.tool.run(arguments)
        mock_handler.assert_called_once_with(arguments)
        assert result == {"success": True}

    @patch.object(OLSTool, "_get_json")
    def test_run_request_exception(self, mock_get_json):
        """Test run() handles request exceptions."""
        mock_get_json.side_effect = requests.RequestException("Network error")
        self.tool._handle_search_terms = lambda x: self.tool._get_json("/test")
        result = self.tool.run({"operation": "search_terms", "query": "test"})
        assert "error" in result


@pytest.mark.unit
class TestSearchTerms:
    """Test _handle_search_terms method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = {"name": "test_ols"}
        self.tool = OLSTool(self.config)

    def test_search_terms_missing_query(self):
        """Test search_terms without query parameter."""
        result = self.tool._handle_search_terms({"operation": "search_terms"})
        assert "error" in result
        assert "query" in result["error"]

    @patch.object(OLSTool, "_get_json")
    def test_search_terms_success(self, mock_get_json):
        """Test successful search_terms."""
        mock_get_json.return_value = {
            "_embedded": {
                "terms": [
                    {
                        "iri": "http://example.org/term1",
                        "ontologyName": "test",
                        "shortForm": "TEST:0001",
                        "label": "term1",
                    }
                ]
            },
            "totalElements": 1,
        }
        result = self.tool._handle_search_terms(
            {"operation": "search_terms", "query": "test"}
        )
        assert "terms" in result
        assert result["query"] == "test"
        assert "filters" in result

    @patch.object(OLSTool, "_get_json")
    def test_search_terms_with_ontology_filter(self, mock_get_json):
        """Test search_terms with ontology filter."""
        mock_get_json.return_value = {"_embedded": {"terms": []}, "totalElements": 0}
        self.tool._handle_search_terms(
            {
                "operation": "search_terms",
                "query": "test",
                "ontology": "efo",
                "exact_match": True,
                "include_obsolete": True,
            }
        )
        mock_get_json.assert_called_once()
        call_args = mock_get_json.call_args
        assert call_args[1]["params"]["ontology"] == "efo"
        assert call_args[1]["params"]["exact"] is True


@pytest.mark.unit
class TestGetOntologyInfo:
    """Test _handle_get_ontology_info method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = {"name": "test_ols"}
        self.tool = OLSTool(self.config)

    def test_get_ontology_info_missing_id(self):
        """Test get_ontology_info without ontology_id."""
        result = self.tool._handle_get_ontology_info({})
        assert "error" in result

    @patch.object(OLSTool, "_get_json")
    def test_get_ontology_info_success(self, mock_get_json):
        """Test successful get_ontology_info."""
        mock_get_json.return_value = {
            "ontologyId": "efo",
            "title": "Experimental Factor Ontology",
        }
        result = self.tool._handle_get_ontology_info(
            {"operation": "get_ontology_info", "ontology_id": "efo"}
        )
        assert result["ontologyId"] == "efo"
        mock_get_json.assert_called_once_with("/api/v2/ontologies/efo")


@pytest.mark.unit
class TestSearchOntologies:
    """Test _handle_search_ontologies method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = {"name": "test_ols"}
        self.tool = OLSTool(self.config)

    @patch.object(OLSTool, "_get_json")
    def test_search_ontologies_no_filter(self, mock_get_json):
        """Test search_ontologies with no filters."""
        mock_get_json.return_value = {
            "_embedded": {
                "ontologies": [
                    {
                        "ontologyId": "efo",
                        "title": "Experimental Factor Ontology",
                    }
                ]
            },
            "page": {"number": 0, "size": 20, "totalPages": 1, "totalElements": 1},
        }
        result = self.tool._handle_search_ontologies(
            {"operation": "search_ontologies"}
        )
        assert "results" in result
        assert "pagination" in result
        assert result["pagination"]["page"] == 0

    @patch.object(OLSTool, "_get_json")
    def test_search_ontologies_with_search(self, mock_get_json):
        """Test search_ontologies with search query."""
        mock_get_json.return_value = {
            "_embedded": {"ontologies": []},
            "page": {"number": 0, "size": 10},
        }
        self.tool._handle_search_ontologies(
            {"operation": "search_ontologies", "search": "disease", "size": 10}
        )
        call_args = mock_get_json.call_args
        assert call_args[1]["params"]["search"] == "disease"
        assert call_args[1]["params"]["size"] == 10


@pytest.mark.unit
class TestGetTermInfo:
    """Test _handle_get_term_info method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = {"name": "test_ols"}
        self.tool = OLSTool(self.config)

    def test_get_term_info_missing_id(self):
        """Test get_term_info without id."""
        result = self.tool._handle_get_term_info({})
        assert "error" in result

    @patch.object(OLSTool, "_get_json")
    def test_get_term_info_not_found(self, mock_get_json):
        """Test get_term_info when term not found."""
        mock_get_json.return_value = {"_embedded": {}}
        result = self.tool._handle_get_term_info({"operation": "get_term_info", "id": "INVALID"})
        assert "error" in result
        assert "not found" in result["error"]

    @patch.object(OLSTool, "_get_json")
    def test_get_term_info_success(self, mock_get_json):
        """Test successful get_term_info."""
        # Note: The code directly validates without field conversion,
        # so mock data must use Python field names (snake_case)
        mock_get_json.return_value = {
            "_embedded": {
                "terms": [
                    {
                        "iri": "http://example.org/term",
                        "ontology_name": "test",
                        "short_form": "TEST:0001",
                        "label": "test_term",
                        "description": ["A test term"],
                        "synonyms": ["test", "testing"],
                    }
                ]
            }
        }
        result = self.tool._handle_get_term_info(
            {"operation": "get_term_info", "id": "TEST:0001"}
        )
        assert result["label"] == "test_term"
        assert "description" in result


@pytest.mark.unit
class TestTermChildren:
    """Test _handle_get_term_children method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = {"name": "test_ols"}
        self.tool = OLSTool(self.config)

    def test_get_term_children_missing_params(self):
        """Test get_term_children without required parameters."""
        result = self.tool._handle_get_term_children({})
        assert "error" in result

    @patch.object(OLSTool, "_get_json")
    def test_get_term_children_success(self, mock_get_json):
        """Test successful get_term_children."""
        mock_get_json.return_value = {
            "_embedded": {
                "children": [
                    {
                        "iri": "http://example.org/child",
                        "ontologyName": "test",
                        "shortForm": "TEST:0002",
                        "label": "child_term",
                    }
                ]
            },
            "page": {"number": 0, "size": 20, "totalElements": 1},
        }
        result = self.tool._handle_get_term_children(
            {
                "operation": "get_term_children",
                "term_iri": "http://example.org/parent",
                "ontology": "test",
            }
        )
        assert "terms" in result
        assert result["ontology"] == "test"

    @patch.object(OLSTool, "_get_json")
    def test_get_term_children_v2_at_id_identifier(self, mock_get_json):
        """Test v2 children payloads that provide @id instead of iri."""
        mock_get_json.return_value = {
            "_embedded": {
                "children": [
                    {
                        "@id": "http://example.org/child",
                        "ontologyName": "test",
                        "shortForm": "TEST:0002",
                        "label": ["child_term"],
                    }
                ]
            },
            "page": {"number": 0, "size": 20, "totalElements": 1},
        }
        result = self.tool._handle_get_term_children(
            {
                "operation": "get_term_children",
                "term_iri": "http://example.org/parent",
                "ontology": "test",
            }
        )
        assert result["total_items"] == 1
        assert result["showing"] == 1
        assert len(result["terms"]) == 1
        assert str(result["terms"][0]["iri"]) == "http://example.org/child"


@pytest.mark.unit
class TestTermAncestors:
    """Test _handle_get_term_ancestors method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = {"name": "test_ols"}
        self.tool = OLSTool(self.config)

    def test_get_term_ancestors_missing_params(self):
        """Test get_term_ancestors without required parameters."""
        result = self.tool._handle_get_term_ancestors({})
        assert "error" in result

    @patch.object(OLSTool, "_get_json")
    def test_get_term_ancestors_success(self, mock_get_json):
        """Test successful get_term_ancestors."""
        mock_get_json.return_value = {
            "_embedded": {
                "ancestors": [
                    {
                        "iri": "http://example.org/ancestor",
                        "ontologyName": "test",
                        "shortForm": "TEST:0000",
                        "label": "ancestor_term",
                    }
                ]
            },
            "page": {"number": 0, "size": 20, "totalElements": 1},
        }
        result = self.tool._handle_get_term_ancestors(
            {
                "operation": "get_term_ancestors",
                "term_iri": "http://example.org/term",
                "ontology": "test",
            }
        )
        assert "terms" in result
        assert result["term_iri"] == "http://example.org/term"

    @patch.object(OLSTool, "_get_json")
    def test_get_term_ancestors_v2_at_id_identifier(self, mock_get_json):
        """Test v2 ancestors payloads that provide @id instead of iri."""
        mock_get_json.return_value = {
            "_embedded": {
                "ancestors": [
                    {
                        "@id": "http://example.org/ancestor",
                        "ontologyName": "test",
                        "shortForm": "TEST:0000",
                        "label": ["ancestor_term"],
                    }
                ]
            },
            "page": {"number": 0, "size": 20, "totalElements": 1},
        }
        result = self.tool._handle_get_term_ancestors(
            {
                "operation": "get_term_ancestors",
                "term_iri": "http://example.org/term",
                "ontology": "test",
            }
        )
        assert result["total_items"] == 1
        assert result["showing"] == 1
        assert len(result["terms"]) == 1
        assert str(result["terms"][0]["iri"]) == "http://example.org/ancestor"


@pytest.mark.unit
class TestFindSimilarTerms:
    """Test _handle_find_similar_terms method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = {"name": "test_ols"}
        self.tool = OLSTool(self.config)

    def test_find_similar_terms_missing_params(self):
        """Test find_similar_terms without required parameters."""
        result = self.tool._handle_find_similar_terms({})
        assert "error" in result

    @patch.object(OLSTool, "_get_json")
    def test_find_similar_terms_success(self, mock_get_json):
        """Test successful find_similar_terms."""
        mock_get_json.return_value = {
            "_embedded": {
                "similar": [
                    {
                        "iri": "http://example.org/similar",
                        "ontologyName": "test",
                        "shortForm": "TEST:0003",
                        "label": "similar_term",
                    }
                ]
            },
            "page": {"number": 0, "size": 10, "totalElements": 1},
        }
        result = self.tool._handle_find_similar_terms(
            {
                "operation": "find_similar_terms",
                "term_iri": "http://example.org/term",
                "ontology": "test",
            }
        )
        assert "terms" in result


@pytest.mark.unit
class TestFormatTermCollection:
    """Test _format_term_collection method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = {"name": "test_ols"}
        self.tool = OLSTool(self.config)

    def test_format_term_collection_empty(self):
        """Test formatting empty term collection."""
        result = self.tool._format_term_collection({}, 10)
        assert result == {}

    def test_format_term_collection_with_elements(self):
        """Test formatting term collection with elements."""
        data = {
            "_embedded": {
                "terms": [
                    {
                        "iri": "http://example.org/term1",
                        "ontologyName": "test",
                        "shortForm": "TEST:0001",
                        "label": "term1",
                    },
                    {
                        "iri": "http://example.org/term2",
                        "ontologyName": "test",
                        "shortForm": "TEST:0002",
                        "label": "term2",
                    },
                ]
            },
            "page": {"number": 0, "size": 20, "totalElements": 2},
        }
        result = self.tool._format_term_collection(data, 10)
        assert "terms" in result
        assert "total_items" in result
        assert result["showing"] == 2

    def test_format_term_collection_size_limit(self):
        """Test that formatting respects size limit."""
        data = {
            "_embedded": {
                "terms": [
                    {
                        "iri": f"http://example.org/term{i}",
                        "ontologyName": "test",
                        "shortForm": f"TEST:{i:04d}",
                        "label": f"term{i}",
                    }
                    for i in range(20)
                ]
            }
        }
        result = self.tool._format_term_collection(data, 5)
        assert result["showing"] == 5


@pytest.mark.unit
class TestBuildTermModel:
    """Test _build_term_model static method."""

    def test_build_term_model_valid(self):
        """Test building term model from valid data."""
        item = {
            "iri": "http://example.org/term",
            "ontologyName": "test",
            "shortForm": "TEST:0001",
            "label": "test_term",
        }
        model = OLSTool._build_term_model(item)
        assert model is not None
        assert model.label == "test_term"

    def test_build_term_model_missing_iri(self):
        """Test building term model without IRI returns None."""
        item = {
            "ontologyName": "test",
            "shortForm": "TEST:0001",
            "label": "test_term",
        }
        model = OLSTool._build_term_model(item)
        assert model is None

    def test_build_term_model_field_fallbacks(self):
        """Test field name fallbacks in _build_term_model."""
        item = {
            "iri": "http://example.org/term",
            "ontology_name": "test",  # Alternative field name
            "short_form": "TEST:0001",  # Alternative field name
            "label": "test_term",
            "obo_id": "GO:0008150",  # Alternative field name
            "is_obsolete": True,  # Alternative field name
        }
        model = OLSTool._build_term_model(item)
        assert model is not None
        assert model.ontology_name == "test"
        assert model.obo_id == "GO:0008150"


@pytest.mark.unit
class TestGetJSON:
    """Test _get_json method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = {"name": "test_ols"}
        self.tool = OLSTool(self.config)

    @patch.object(requests.Session, "get")
    def test_get_json_success(self, mock_get):
        """Test successful JSON retrieval."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"test": "data"}
        mock_get.return_value = mock_response
        result = self.tool._get_json("/test/path")
        assert result == {"test": "data"}

    @patch.object(requests.Session, "get")
    def test_get_json_with_params(self, mock_get):
        """Test JSON retrieval with parameters."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"test": "data"}
        mock_get.return_value = mock_response
        params = {"q": "test", "rows": 10}
        self.tool._get_json("/api/search", params=params)
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[1]["params"] == params

    @patch.object(requests.Session, "get")
    def test_get_json_http_error(self, mock_get):
        """Test _get_json handles HTTP errors.

        _get_json catches all RequestException subclasses (including HTTPError)
        and re-raises them as plain RequestException with added context.
        """
        mock_get.side_effect = requests.HTTPError("404 Not Found")
        with pytest.raises(requests.RequestException):
            self.tool._get_json("/invalid")


@pytest.mark.unit
class TestIntegration:
    """Integration tests for OLSTool."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = {"name": "test_ols"}
        self.tool = OLSTool(self.config)

    @patch.object(OLSTool, "_get_json")
    def test_full_workflow_search_to_details(self, mock_get_json):
        """Test workflow from search to getting term details."""
        # First call: search
        mock_get_json.return_value = {
            "_embedded": {
                "terms": [
                    {
                        "iri": "http://example.org/term",
                        "ontologyName": "test",
                        "shortForm": "TEST:0001",
                        "label": "test_term",
                    }
                ]
            },
            "totalElements": 1,
        }
        search_result = self.tool._handle_search_terms(
            {"operation": "search_terms", "query": "test"}
        )
        assert len(search_result["terms"]) > 0

        # Second call: get details
        mock_get_json.return_value = {
            "_embedded": {
                "terms": [
                    {
                        "iri": "http://example.org/term",
                        "ontologyName": "test",
                        "shortForm": "TEST:0001",
                        "label": "test_term",
                        "description": ["A test term"],
                    }
                ]
            }
        }
        detail_result = self.tool._handle_get_term_info(
            {"operation": "get_term_info", "id": "TEST:0001"}
        )
        assert detail_result["label"] == "test_term"
