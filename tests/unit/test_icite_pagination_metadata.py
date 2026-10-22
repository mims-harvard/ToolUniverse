from unittest.mock import MagicMock, patch

from tooluniverse.icite_tool import ICiteSearchPublicationsTool


def _response(payload):
    response = MagicMock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


def _tool():
    return ICiteSearchPublicationsTool({"name": "iCite_search_publications"})


@patch("tooluniverse.icite_tool.request_with_retry")
def test_pubmed_offset_and_exact_total_are_exposed(mock_request):
    mock_request.side_effect = [
        _response(
            {
                "esearchresult": {
                    "count": "12345",
                    "idlist": ["401", "402", "403"],
                }
            }
        ),
        _response(
            {
                "data": [
                    {"pmid": 401, "citation_count": 1},
                    {"pmid": 402, "citation_count": 9},
                    {"pmid": 403, "citation_count": 3},
                ]
            }
        ),
    ]

    result = _tool().run({"query": "BRCA1", "limit": 3, "offset": 1200})

    pubmed_params = mock_request.call_args_list[0].kwargs["params"]
    assert pubmed_params["retstart"] == 1200
    assert pubmed_params["retmax"] == 3
    assert result["metadata"]["total_results"] == 12345
    assert result["metadata"]["next_offset"] == 1203
    assert result["metadata"]["sort_scope"] == "current PubMed relevance page"
    assert [row["pmid"] for row in result["data"]] == [402, 403, 401]


@patch("tooluniverse.icite_tool.request_with_retry")
def test_missing_icite_record_is_not_silent(mock_request):
    mock_request.side_effect = [
        _response({"esearchresult": {"count": "2", "idlist": ["401", "402"]}}),
        _response({"data": [{"pmid": 401, "citation_count": 1}]}),
    ]

    result = _tool().run({"query": "BRCA1", "limit": 2})

    assert result["metadata"]["enrichment_complete"] is False
    assert result["metadata"]["missing_icite_pmids"] == ["402"]
    assert result["metadata"]["returned"] == 1


@patch("tooluniverse.icite_tool.request_with_retry")
def test_inconsistent_empty_pubmed_page_is_marked_stalled(mock_request):
    pubmed = MagicMock(status_code=200)
    pubmed.raise_for_status.return_value = None
    pubmed.json.return_value = {"esearchresult": {"count": "100", "idlist": []}}
    mock_request.return_value = pubmed

    result = _tool().run({"query": "CRISPR", "limit": 2, "offset": 10})

    assert result["status"] == "success"
    assert result["metadata"]["pagination_stalled"] is True
    assert result["metadata"]["has_more"] is False
    assert result["metadata"]["next_offset"] is None
    assert "Do not retry" in result["metadata"]["warning"]


@patch("tooluniverse.icite_tool.request_with_retry")
def test_direct_call_rejects_string_pagination(mock_request):
    for pagination in ({"limit": "2"}, {"offset": "2"}):
        result = _tool().run({"query": "CRISPR", **pagination})
        assert result["status"] == "error"
    mock_request.assert_not_called()
