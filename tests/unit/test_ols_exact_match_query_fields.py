"""Regression tests for ``ols_search_terms``'s ``exact_match`` filter.

OLS4's ``/api/search?exact=true`` flag restricts nothing on its own: the endpoint
searches label, synonym, description, iri, short_form and obo_id by default, so
an "exact" hit against a description token still returns the whole
neighbourhood. ``q=fibroblast&ontology=cl&exact=true`` returned 167 of the 168
terms that the unfiltered search returns, while the response echoed
``"exact_match": true`` back to the caller as though the filter had been applied.

The fix constrains ``queryFields`` whenever exact matching is requested. These
tests pin the request-parameter construction without touching the network.
"""

from unittest.mock import patch

import pytest

from tooluniverse.ols_tool import OLSTool

EMPTY_SOLR_RESPONSE = {"response": {"docs": [], "numFound": 0}}


def _params(mock_get_json):
    """Return the query params handed to the single ``_get_json`` call."""

    mock_get_json.assert_called_once()
    return mock_get_json.call_args[1]["params"]


@pytest.fixture
def tool():
    return OLSTool({"name": "test_ols"})


@pytest.mark.unit
class TestExactMatchQueryFields:
    """``exact_match`` must constrain the fields OLS matches against."""

    @patch.object(OLSTool, "_get_json")
    def test_exact_match_sends_query_fields(self, mock_get_json, tool):
        mock_get_json.return_value = EMPTY_SOLR_RESPONSE
        tool._handle_search_terms(
            {"operation": "search_terms", "query": "fibroblast", "exact_match": True}
        )
        params = _params(mock_get_json)
        assert params["exact"] is True
        assert params["queryFields"] == "label,synonym"

    @patch.object(OLSTool, "_get_json")
    def test_non_exact_search_sends_no_query_fields(self, mock_get_json, tool):
        mock_get_json.return_value = EMPTY_SOLR_RESPONSE
        tool._handle_search_terms(
            {"operation": "search_terms", "query": "fibroblast", "exact_match": False}
        )
        params = _params(mock_get_json)
        assert params["exact"] is False
        assert "queryFields" not in params

    @patch.object(OLSTool, "_get_json")
    def test_exact_match_defaults_to_off(self, mock_get_json, tool):
        mock_get_json.return_value = EMPTY_SOLR_RESPONSE
        tool._handle_search_terms({"operation": "search_terms", "query": "fibroblast"})
        assert "queryFields" not in _params(mock_get_json)

    @pytest.mark.parametrize(
        "query",
        ["CL:0000084", "CL_0000084", "http://purl.obolibrary.org/obo/CL_0000084"],
    )
    @patch.object(OLSTool, "_get_json")
    def test_identifier_queries_match_identifier_fields(
        self, mock_get_json, tool, query
    ):
        """Constraining an ID lookup to label/synonym would return zero hits."""

        mock_get_json.return_value = EMPTY_SOLR_RESPONSE
        tool._handle_search_terms(
            {"operation": "search_terms", "query": query, "exact_match": True}
        )
        assert _params(mock_get_json)["queryFields"] == "obo_id,short_form,iri"

    @pytest.mark.parametrize(
        "query",
        ["type 2 diabetes mellitus", "T-lymphocyte", "T cell", "5-HT"],
    )
    @patch.object(OLSTool, "_get_json")
    def test_name_queries_match_name_fields(self, mock_get_json, tool, query):
        mock_get_json.return_value = EMPTY_SOLR_RESPONSE
        tool._handle_search_terms(
            {"operation": "search_terms", "query": query, "exact_match": True}
        )
        assert _params(mock_get_json)["queryFields"] == "label,synonym"


@pytest.mark.unit
class TestExactMatchFiltersEcho:
    """The echoed ``filters`` block must be a verifiable claim."""

    @patch.object(OLSTool, "_get_json")
    def test_filters_report_the_matched_fields(self, mock_get_json, tool):
        mock_get_json.return_value = EMPTY_SOLR_RESPONSE
        result = tool._handle_search_terms(
            {
                "operation": "search_terms",
                "query": "fibroblast",
                "ontology": "cl",
                "exact_match": True,
            }
        )
        assert result["filters"]["exact_match"] is True
        assert result["filters"]["exact_match_fields"] == "label,synonym"

    @patch.object(OLSTool, "_get_json")
    def test_filters_omit_matched_fields_when_not_exact(self, mock_get_json, tool):
        mock_get_json.return_value = EMPTY_SOLR_RESPONSE
        result = tool._handle_search_terms(
            {"operation": "search_terms", "query": "fibroblast", "ontology": "cl"}
        )
        assert result["filters"]["exact_match"] is False
        assert "exact_match_fields" not in result["filters"]
