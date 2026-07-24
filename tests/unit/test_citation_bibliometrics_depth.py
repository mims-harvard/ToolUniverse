"""Mocked-HTTP unit tests for the citation-bibliometrics depth tools.

Covers five new config-only tools that reuse the existing BaseRESTTool class
(no new @register_tool class, no registration changes):

  * SemanticScholar_get_paper_citations  -- per-citing-paper enumeration with
    citation intents, isInfluential flag, and citing-sentence contexts.
  * SemanticScholar_get_paper_references  -- per-reference enumeration with
    intents/isInfluential for a paper's bibliography.
  * SemanticScholar_get_author_papers  -- an author's publication list with
    per-paper citation counts and years.
  * DBLP_search_authors  -- DBLP author disambiguation (PID URL, affiliations,
    aliases, awards).
  * DBLP_search_venues  -- DBLP venue resolution (acronym/name -> venue record).

Each tool is loaded from its real JSON config so the tests exercise the actual
endpoint templates and param maps. HTTP is mocked, so these run offline. Both a
successful parse path and an error path are covered per tool.
"""
import json
import os

import pytest

from tooluniverse import base_rest_tool
from tooluniverse.base_rest_tool import BaseRESTTool

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "src",
    "tooluniverse",
    "data",
)


def _load_config(filename, tool_name):
    with open(os.path.join(DATA_DIR, filename)) as fh:
        for entry in json.load(fh):
            if entry.get("name") == tool_name:
                return entry
    raise AssertionError(f"{tool_name} not found in {filename}")


class _FakeResponse:
    def __init__(self, status_code=200, json_data=None, text="", url="http://x"):
        self.status_code = status_code
        self._json = json_data
        self.text = text if text else (json.dumps(json_data) if json_data else "")
        self.url = url
        self.headers = {"content-type": "application/json"}
        self.reason = "OK" if status_code == 200 else "Error"

    def json(self):
        if self._json is None:
            raise ValueError("no json")
        return self._json


# ---------------------------------------------------------------------------
# 1. SemanticScholar_get_paper_citations
# ---------------------------------------------------------------------------
@pytest.mark.unit
def test_s2_paper_citations_parse(monkeypatch):
    """Citations parse: path id substituted, intents/isInfluential/contexts kept."""
    cfg = _load_config(
        "semantic_scholar_ext_tools.json", "SemanticScholar_get_paper_citations"
    )
    tool = BaseRESTTool(cfg)

    payload = {
        "offset": 0,
        "next": 2,
        "data": [
            {
                "intents": ["methodology"],
                "isInfluential": True,
                "contexts": ["We build on the Transformer architecture ..."],
                "citingPaper": {
                    "paperId": "749e78f16f1c7b84e2a3cd7b598f48ad30a0d354",
                    "title": "A citing paper",
                    "year": 2024,
                },
            },
            {
                "intents": [],
                "isInfluential": False,
                "contexts": [],
                "citingPaper": {"paperId": "bcc703d6", "title": "Another", "year": 2025},
            },
        ],
    }
    captured = {}

    def fake_request(session, method, url, params=None, **kwargs):
        captured["url"] = url
        captured["params"] = params
        return _FakeResponse(200, json_data=payload, url=url)

    monkeypatch.setattr(base_rest_tool, "request_with_retry", fake_request)

    out = tool.run(
        {"paper_id": "649def34f8be52c8b66281af98ae884c09aef38b", "limit": 2}
    )
    assert out["status"] == "success"
    # paper_id is a path param and must be substituted into the URL, not sent as query
    assert "649def34f8be52c8b66281af98ae884c09aef38b" in captured["url"]
    assert captured["url"].endswith("/citations")
    assert "paper_id" not in captured["params"]
    rows = out["data"]["data"]
    assert rows[0]["isInfluential"] is True
    assert rows[0]["intents"] == ["methodology"]
    assert rows[0]["contexts"][0].startswith("We build on")
    assert rows[0]["citingPaper"]["title"] == "A citing paper"


@pytest.mark.unit
def test_s2_paper_citations_error_path(monkeypatch):
    """Citations error path: non-2xx yields a status=error envelope, no raise."""
    cfg = _load_config(
        "semantic_scholar_ext_tools.json", "SemanticScholar_get_paper_citations"
    )
    tool = BaseRESTTool(cfg)

    def fake_request(session, method, url, params=None, **kwargs):
        return _FakeResponse(404, json_data=None, text="Not Found", url=url)

    monkeypatch.setattr(base_rest_tool, "request_with_retry", fake_request)

    out = tool.run({"paper_id": "NOT_A_REAL_ID", "limit": 2})
    assert out["status"] == "error"
    assert out["status_code"] == 404
    assert "error" in out


# ---------------------------------------------------------------------------
# 2. SemanticScholar_get_paper_references
# ---------------------------------------------------------------------------
@pytest.mark.unit
def test_s2_paper_references_parse(monkeypatch):
    """References parse: citedPaper wrapper with intents/isInfluential preserved."""
    cfg = _load_config(
        "semantic_scholar_ext_tools.json", "SemanticScholar_get_paper_references"
    )
    tool = BaseRESTTool(cfg)

    payload = {
        "offset": 0,
        "citingPaperInfo": {"title": "Attention Is All You Need"},
        "next": 2,
        "data": [
            {
                "isInfluential": False,
                "intents": ["background"],
                "contexts": [],
                "citedPaper": {
                    "paperId": "1fec9d41",
                    "title": "Construction of the Literature Graph in Semantic Scholar",
                    "year": 2018,
                },
            }
        ],
    }
    captured = {}

    def fake_request(session, method, url, params=None, **kwargs):
        captured["url"] = url
        return _FakeResponse(200, json_data=payload, url=url)

    monkeypatch.setattr(base_rest_tool, "request_with_retry", fake_request)

    out = tool.run(
        {"paper_id": "649def34f8be52c8b66281af98ae884c09aef38b", "limit": 2}
    )
    assert out["status"] == "success"
    assert captured["url"].endswith("/references")
    rows = out["data"]["data"]
    assert rows[0]["intents"] == ["background"]
    assert rows[0]["isInfluential"] is False
    assert "Literature Graph" in rows[0]["citedPaper"]["title"]


@pytest.mark.unit
def test_s2_paper_references_error_path(monkeypatch):
    """References error path: non-2xx yields a status=error envelope, no raise."""
    cfg = _load_config(
        "semantic_scholar_ext_tools.json", "SemanticScholar_get_paper_references"
    )
    tool = BaseRESTTool(cfg)

    def fake_request(session, method, url, params=None, **kwargs):
        return _FakeResponse(500, json_data=None, text="Server Error", url=url)

    monkeypatch.setattr(base_rest_tool, "request_with_retry", fake_request)

    out = tool.run({"paper_id": "X", "limit": 2})
    assert out["status"] == "error"
    assert out["status_code"] == 500


# ---------------------------------------------------------------------------
# 3. SemanticScholar_get_author_papers
# ---------------------------------------------------------------------------
@pytest.mark.unit
def test_s2_author_papers_parse(monkeypatch):
    """Author papers parse: per-paper year and citationCount preserved."""
    cfg = _load_config(
        "semantic_scholar_ext_tools.json", "SemanticScholar_get_author_papers"
    )
    tool = BaseRESTTool(cfg)

    payload = {
        "offset": 0,
        "next": 2,
        "data": [
            {
                "paperId": "cb92a7f9",
                "title": "The Semantic Scholar Open Data Platform",
                "year": 2023,
                "citationCount": 179,
            },
            {
                "paperId": "6c5c6f88",
                "title": "A Computational Inflection for Scientific Discovery",
                "year": 2022,
                "citationCount": 46,
            },
        ],
    }
    captured = {}

    def fake_request(session, method, url, params=None, **kwargs):
        captured["url"] = url
        captured["params"] = params
        return _FakeResponse(200, json_data=payload, url=url)

    monkeypatch.setattr(base_rest_tool, "request_with_retry", fake_request)

    out = tool.run({"author_id": "1741101", "limit": 2})
    assert out["status"] == "success"
    # author_id is a path param substituted into the URL
    assert "/author/1741101/papers" in captured["url"]
    assert "author_id" not in captured["params"]
    papers = out["data"]["data"]
    assert papers[0]["year"] == 2023
    assert papers[0]["citationCount"] == 179
    assert papers[1]["title"].startswith("A Computational Inflection")


@pytest.mark.unit
def test_s2_author_papers_error_path(monkeypatch):
    """Author papers error path: non-2xx yields a status=error envelope."""
    cfg = _load_config(
        "semantic_scholar_ext_tools.json", "SemanticScholar_get_author_papers"
    )
    tool = BaseRESTTool(cfg)

    def fake_request(session, method, url, params=None, **kwargs):
        return _FakeResponse(404, json_data=None, text="Not Found", url=url)

    monkeypatch.setattr(base_rest_tool, "request_with_retry", fake_request)

    out = tool.run({"author_id": "0000000", "limit": 2})
    assert out["status"] == "error"
    assert out["status_code"] == 404


# ---------------------------------------------------------------------------
# 4. DBLP_search_authors
# ---------------------------------------------------------------------------
@pytest.mark.unit
def test_dblp_search_authors_parse(monkeypatch):
    """DBLP author parse: query->q, limit->h, format=json; PID/affiliation/award."""
    cfg = _load_config("dblp_tools.json", "DBLP_search_authors")
    tool = BaseRESTTool(cfg)

    payload = {
        "result": {
            "query": "yann* lecun*",
            "status": {"@code": "200", "text": "OK"},
            "hits": {
                "@total": "1",
                "hit": [
                    {
                        "@id": "12345",
                        "@score": "3",
                        "info": {
                            "author": "Yann LeCun",
                            "url": "https://dblp.org/pid/l/YannLeCun",
                            "notes": {
                                "note": [
                                    {"@type": "affiliation", "text": "New York University"},
                                    {"@type": "affiliation", "text": "Facebook"},
                                    {"@type": "award", "text": "Turing Award"},
                                ]
                            },
                        },
                    }
                ],
            },
        }
    }
    captured = {}

    def fake_request(session, method, url, params=None, **kwargs):
        captured["url"] = url
        captured["params"] = params
        return _FakeResponse(200, json_data=payload, url=url)

    monkeypatch.setattr(base_rest_tool, "request_with_retry", fake_request)

    out = tool.run({"query": "yann lecun", "limit": 3})
    assert out["status"] == "success"
    # param_mapping: query -> q, limit -> h; fixed format=json from fields.params
    assert captured["params"].get("q") == "yann lecun"
    assert captured["params"].get("h") == 3
    assert captured["params"].get("format") == "json"
    # original arg names must NOT leak through as query params
    assert "query" not in captured["params"]
    assert "limit" not in captured["params"]
    info = out["data"]["result"]["hits"]["hit"][0]["info"]
    assert info["author"] == "Yann LeCun"
    assert info["url"].endswith("/YannLeCun")
    award_notes = [n for n in info["notes"]["note"] if n["@type"] == "award"]
    assert award_notes[0]["text"] == "Turing Award"


@pytest.mark.unit
def test_dblp_search_authors_error_path(monkeypatch):
    """DBLP author error path: non-2xx yields a status=error envelope."""
    cfg = _load_config("dblp_tools.json", "DBLP_search_authors")
    tool = BaseRESTTool(cfg)

    def fake_request(session, method, url, params=None, **kwargs):
        return _FakeResponse(503, json_data=None, text="Service Unavailable", url=url)

    monkeypatch.setattr(base_rest_tool, "request_with_retry", fake_request)

    out = tool.run({"query": "anyone", "limit": 1})
    assert out["status"] == "error"
    assert out["status_code"] == 503


# ---------------------------------------------------------------------------
# 5. DBLP_search_venues
# ---------------------------------------------------------------------------
@pytest.mark.unit
def test_dblp_search_venues_parse(monkeypatch):
    """DBLP venue parse: query->q, limit->h, venue record fields preserved."""
    cfg = _load_config("dblp_tools.json", "DBLP_search_venues")
    tool = BaseRESTTool(cfg)

    payload = {
        "result": {
            "query": "ICML*",
            "status": {"@code": "200", "text": "OK"},
            "hits": {
                "@total": "1",
                "hit": [
                    {
                        "@id": "4166",
                        "@score": "1",
                        "info": {
                            "venue": "International Conference on Machine Learning (ICML)",
                            "acronym": "ICML",
                            "type": "Conference or Workshop",
                            "url": "https://dblp.org/db/conf/icml/",
                        },
                    }
                ],
            },
        }
    }
    captured = {}

    def fake_request(session, method, url, params=None, **kwargs):
        captured["url"] = url
        captured["params"] = params
        return _FakeResponse(200, json_data=payload, url=url)

    monkeypatch.setattr(base_rest_tool, "request_with_retry", fake_request)

    out = tool.run({"query": "ICML", "limit": 1})
    assert out["status"] == "success"
    assert captured["params"].get("q") == "ICML"
    assert captured["params"].get("h") == 1
    assert captured["params"].get("format") == "json"
    assert captured["url"].endswith("/search/venue/api")
    info = out["data"]["result"]["hits"]["hit"][0]["info"]
    assert info["acronym"] == "ICML"
    assert "Machine Learning" in info["venue"]
    assert info["type"].startswith("Conference")


@pytest.mark.unit
def test_dblp_search_venues_error_path(monkeypatch):
    """DBLP venue error path: non-2xx yields a status=error envelope."""
    cfg = _load_config("dblp_tools.json", "DBLP_search_venues")
    tool = BaseRESTTool(cfg)

    def fake_request(session, method, url, params=None, **kwargs):
        return _FakeResponse(500, json_data=None, text="Internal Error", url=url)

    monkeypatch.setattr(base_rest_tool, "request_with_retry", fake_request)

    out = tool.run({"query": "ICML", "limit": 1})
    assert out["status"] == "error"
    assert out["status_code"] == 500
