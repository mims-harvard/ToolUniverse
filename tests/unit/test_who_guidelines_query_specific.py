"""Regression guard for Fix-R56-1: WHO_Guidelines_Search answered every
query with the same three documents.

The tool derived a slug from the query and scraped
``who.int/health-topics/<slug>``. Confirmed live that this 404s for
anything WHO does not treat as a health topic -- "methadone",
"clozapine" and the nonsense token "zzqqxxwubble" all returned HTTP 404,
while "tuberculosis", "malaria" and "trachoma" returned 200. On a 404 the
tool fell back to scraping WHO's generic recent-guidelines listing, so
all three queries produced byte-identical output (md5 37f5515bc0),
presented as results for the query asked.

The fallback now searches WHO IRIS, WHO's official institutional
repository, over its DSpace REST API. Confirmed live that IRIS is
genuinely query-responsive: methadone 1027 hits, clozapine 324,
trachoma 3964, "zzqqxxwubble" 0.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.unified_guideline_tools import WHOGuidelinesTool

pytestmark = pytest.mark.unit


def _tool():
    return WHOGuidelinesTool(
        {"name": "WHO_Guidelines_Search", "type": "WHOGuidelinesTool"}
    )


def _iris_payload(*titles):
    return {
        "_embedded": {
            "searchResult": {
                "page": {"totalElements": len(titles)},
                "_embedded": {
                    "objects": [
                        {
                            "_embedded": {
                                "indexableObject": {
                                    "name": title,
                                    "handle": f"10665/{1000 + i}",
                                    "metadata": {
                                        "dc.type": [{"value": "Journal articles"}],
                                        "dc.date.issued": [{"value": "2006-12-31"}],
                                    },
                                }
                            }
                        }
                        for i, title in enumerate(titles)
                    ]
                },
            }
        }
    }


def _response(*, status=200, json_body=None, html=b""):
    resp = MagicMock()
    resp.status_code = status
    resp.content = html
    resp.json.return_value = json_body if json_body is not None else {}
    resp.raise_for_status.return_value = None
    return resp


TOPIC_HTML = (
    b"<html><body>"
    b'<a href="/publications/i/item/9789240001503">'
    b"WHO consolidated guidelines on tuberculosis: Module 1</a>"
    b"</body></html>"
)

# What who.int/publications/who-guidelines actually serves: WHO's most
# recent guidelines, unrelated to any particular query. The old code
# returned these on every topic miss, so a test that serves an empty page
# here would pass against the bug for the wrong reason.
GENERIC_LISTING_HTML = (
    b"<html><body>"
    b'<a href="/publications/i/item/9789240124233">'
    b"Consolidated HIV guidelines: service delivery</a>"
    b'<a href="/publications/i/item/9789240121805">'
    b"Guidelines for the prevention of bloodstream infections</a>"
    b'<a href="/publications/i/item/9789240121744">'
    b"WHO guideline for screening and treatment of cervical pre-cancer lesions</a>"
    b"</body></html>"
)


class TestQuerySpecificResults:
    def test_topic_miss_searches_iris_not_the_generic_listing(self):
        """A query with no WHO health topic must not fall back to WHO's
        recent-guidelines page."""
        tool = _tool()
        requested = []

        def fake_get(url, **kwargs):
            requested.append((url, kwargs.get("params")))
            if "/health-topics/" in url:
                return _response(status=404)
            return _response(json_body=_iris_payload("Methadone for pain"))

        with patch.object(tool.session, "get", side_effect=fake_get):
            results = tool.run({"query": "methadone", "limit": 3})

        urls = [u for u, _ in requested]
        assert not any("who-guidelines" in u for u in urls), (
            "generic recent-guidelines listing was scraped again: " f"{urls}"
        )
        iris_calls = [(u, p) for u, p in requested if "iris.who.int" in u]
        assert len(iris_calls) == 1
        # The query reaches the search backend unaltered.
        assert iris_calls[0][1]["query"] == "methadone"
        assert [r["title"] for r in results] == ["Methadone for pain"]
        assert results[0]["url"] == "https://iris.who.int/handle/10665/1000"
        assert results[0]["matched_via"] == "iris_search"

    def test_no_upstream_match_returns_empty_not_unrelated_documents(self):
        """The nonsense token that used to return three real WHO guidelines.

        The generic listing is served here exactly as who.int serves it, so
        this fails against the old fallback rather than passing because the
        stub happened to be empty.
        """
        tool = _tool()

        def fake_get(url, **kwargs):
            if "/health-topics/" in url:
                return _response(status=404)
            if "who-guidelines" in url:
                return _response(html=GENERIC_LISTING_HTML)
            return _response(json_body=_iris_payload())

        with patch.object(tool.session, "get", side_effect=fake_get):
            results = tool.run({"query": "zzqqxxwubble", "limit": 3})

        assert results == []

    def test_distinct_queries_get_distinct_results(self):
        tool = _tool()

        def fake_get(url, **kwargs):
            if "/health-topics/" in url:
                return _response(status=404)
            return _response(
                json_body=_iris_payload(f"Document about {kwargs['params']['query']}")
            )

        with patch.object(tool.session, "get", side_effect=fake_get):
            first = tool.run({"query": "methadone", "limit": 3})
            second = tool.run({"query": "clozapine", "limit": 3})

        assert json.dumps(first) != json.dumps(second)

    def test_iris_results_do_not_claim_to_be_guidelines_by_default(self):
        """IRIS has no 'guideline' document type, so the flag must come
        from the record rather than being asserted for every hit."""
        tool = _tool()

        def fake_get(url, **kwargs):
            if "/health-topics/" in url:
                return _response(status=404)
            return _response(
                json_body=_iris_payload(
                    "Clozapine : revised monitoring frequency",
                    "Guidelines on methadone therapy in Myanmar",
                )
            )

        with patch.object(tool.session, "get", side_effect=fake_get):
            results = tool.run({"query": "methadone", "limit": 5})

        assert results[0]["is_guideline"] is False
        assert results[1]["is_guideline"] is True
        assert results[0]["document_type"] == "Journal articles"

    def test_health_topic_hit_still_answers_and_says_so(self):
        tool = _tool()

        def fake_get(url, **kwargs):
            assert "iris.who.int" not in url, "IRIS queried despite a topic hit"
            return _response(html=TOPIC_HTML)

        with patch.object(tool.session, "get", side_effect=fake_get):
            results = tool.run({"query": "tuberculosis", "limit": 3})

        assert len(results) == 1
        assert results[0]["matched_via"] == "health_topic:tuberculosis"
        assert results[0]["url"].startswith("https://www.who.int/publications/")

    def test_limit_is_honoured_on_the_iris_path(self):
        tool = _tool()

        def fake_get(url, **kwargs):
            if "/health-topics/" in url:
                return _response(status=404)
            return _response(json_body=_iris_payload("a", "b", "c", "d", "e"))

        with patch.object(tool.session, "get", side_effect=fake_get):
            results = tool.run({"query": "methadone", "limit": 2})

        assert len(results) == 2
