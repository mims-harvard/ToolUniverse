from unittest.mock import Mock, patch

import pytest

from tooluniverse.dblp_tool import DBLPTool


pytestmark = pytest.mark.unit


def _response(*, total="10", computed="10", first="2"):
    response = Mock(status_code=200, reason="OK")
    response.json.return_value = {
        "result": {
            "hits": {
                "@total": total,
                "@computed": computed,
                "@sent": "2",
                "@first": first,
                "hit": [
                    {
                        "info": {
                            "title": "Research &amp; Development",
                            "authors": {
                                "author": {
                                    "@pid": "1/Someone",
                                    "text": "A. O&apos;Neil",
                                }
                            },
                            "year": "2024",
                            "venue": "Journal &amp; Systems",
                            "url": "https://dblp.org/rec/journals/x/One24",
                            "ee": [
                                "https://example.org/fulltext",
                                "https://doi.org/10.1000/example",
                            ],
                            "type": "Journal Articles",
                        }
                    },
                    {
                        "info": {
                            "title": "Proceedings paper",
                            "authors": {"author": []},
                            "type": "Conference and Workshop Papers",
                        }
                    },
                ],
            }
        }
    }
    return response


def test_dblp_forwards_offset_and_reports_exact_continuation():
    tool = DBLPTool({"name": "DBLP_search_publications"})
    with patch("tooluniverse.dblp_tool.requests.get", return_value=_response()) as get:
        results = tool.run({"query": "machine learning", "limit": 2, "offset": 2})

    assert get.call_args.kwargs["params"] == {
        "q": "machine learning",
        "h": 2,
        "f": 2,
        "format": "json",
    }
    pagination = results[0]["search_pagination"]
    assert pagination["total_matches"] == 10
    assert pagination["accessible_results"] == 10
    assert pagination["upstream_truncated"] is False
    assert pagination["has_more"] is True
    assert pagination["next_offset"] == 4


def test_dblp_does_not_fabricate_missing_bibliometric_facts():
    tool = DBLPTool({"name": "DBLP_search_publications"})
    with patch("tooluniverse.dblp_tool.requests.get", return_value=_response()):
        paper = tool.run({"query": "systems", "limit": 2, "offset": 2})[0]

    assert paper["title"] == "Research & Development"
    assert paper["authors"][0]["text"] == "A. O'Neil"
    assert paper["venue"] == "Journal & Systems"
    assert paper["doi"] == "10.1000/example"
    assert paper["publication_type"] == "Journal Articles"
    assert paper["article_type"] == "journal-article"
    assert paper["abstract"] is None
    assert paper["citations"] is None
    assert paper["open_access"] is None
    assert paper["keywords"] == []
    assert paper["publisher"] is None
    assert "citation_count" in paper["unavailable_fields"]
    assert paper["data_quality"]["has_open_access_status"] is False


def test_dblp_discloses_the_computed_result_window():
    tool = DBLPTool({"name": "DBLP_search_publications"})
    with patch(
        "tooluniverse.dblp_tool.requests.get",
        return_value=_response(total="92853", computed="100", first="98"),
    ):
        results = tool.run({"query": "machine learning", "limit": 2, "offset": 98})

    pagination = results[0]["search_pagination"]
    assert pagination["total_matches"] == 92853
    assert pagination["accessible_results"] == 100
    assert pagination["upstream_truncated"] is True
    assert pagination["has_more"] is False
    assert pagination["next_offset"] is None
    assert "refine the query" in pagination["warning"]


@pytest.mark.parametrize("limit", [0, 1001, True, 1.5, "10"])
def test_dblp_rejects_invalid_limits_before_network(limit):
    tool = DBLPTool({"name": "DBLP_search_publications"})
    with patch("tooluniverse.dblp_tool.requests.get") as get:
        result = tool.run({"query": "systems", "limit": limit})

    assert result["status"] == "error"
    assert result["parameter"] == "limit"
    get.assert_not_called()


@pytest.mark.parametrize("offset", [-1, True, 1.5, "2"])
def test_dblp_rejects_invalid_offsets_before_network(offset):
    tool = DBLPTool({"name": "DBLP_search_publications"})
    with patch("tooluniverse.dblp_tool.requests.get") as get:
        result = tool.run({"query": "systems", "offset": offset})

    assert result["status"] == "error"
    assert result["parameter"] == "offset"
    get.assert_not_called()
