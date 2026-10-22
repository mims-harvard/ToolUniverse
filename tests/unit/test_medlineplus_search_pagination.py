"""Regressions for complete, reachable MedlinePlus search results."""

import pytest

from tooluniverse.medlineplus_tool import MedlinePlusRESTTool

pytestmark = pytest.mark.unit


def _tool():
    return MedlinePlusRESTTool(
        {
            "name": "MedlinePlus_search_topics_by_keyword",
            "fields": {"endpoint": "https://example.test/query"},
            "parameter": {"properties": {}},
        }
    )


def test_search_formatter_keeps_full_summaries_and_exposes_next_page():
    long_summary = "Complete upstream health-topic evidence. " * 40
    payload = {
        "nlmSearchResult": {
            "count": "12",
            "retstart": "3",
            "retmax": "2",
            "list": {
                "@num": "12",
                "@start": "3",
                "@per": "2",
                "document": [
                    {
                        "@rank": "4",
                        "@url": "https://medlineplus.gov/a.html",
                        "content": {
                            "health-topic": {
                                "@title": "Topic A",
                                "@url": "https://medlineplus.gov/a.html",
                                "@language": "English",
                                "full-summary": long_summary,
                            }
                        },
                    },
                    {
                        "@rank": "5",
                        "content": {
                            "health-topic": {
                                "@title": "Topic B",
                                "full-summary": "Short summary",
                            }
                        },
                    },
                ],
            },
        }
    }

    result = _tool()._format_response(payload, "MedlinePlus_search_topics_by_keyword")

    assert len(long_summary) > 500
    assert result["topics"][0]["summary"] == long_summary
    assert result["topics"][0]["summary_length"] == len(long_summary)
    assert result["total_available"] == 12
    assert result["returned"] == 2
    assert result["offset"] == 3
    assert result["limit"] == 2
    assert result["has_more"] is True
    assert result["next_offset"] == 5


def test_empty_page_is_valid_and_reports_completion_instead_of_parse_error():
    payload = {
        "nlmSearchResult": {
            "count": "12",
            "retstart": "12",
            "retmax": "10",
            "list": {"@num": "12", "@start": "12", "@per": "10"},
        }
    }

    result = _tool()._format_response(payload, "MedlinePlus_search_topics_by_keyword")

    assert result["topics"] == []
    assert result["returned"] == 0
    assert result["offset"] == 12
    assert result["has_more"] is False
    assert result["next_offset"] is None
