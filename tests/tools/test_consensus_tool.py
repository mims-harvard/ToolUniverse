"""Unit tests for the Consensus search tool.

No real CONSENSUS_API_KEY is available in this environment (Consensus
requires a paid account), so these tests mock the HTTP layer rather than
call the live API, matching the established convention for API-key-gated
tools (see test_semantic_scholar_tool_resilience.py). The fixture response
shape is copied from Consensus's own published API documentation
(https://github.com/Consensus-NLP/consensus-api), not invented, but it has
not been verified against a real live response and should be re-checked
against a real key before this tool ships to real users.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.consensus_tool import ConsensusTool


class _FakeResponse:
    def __init__(self, status_code=200, payload=None, reason=""):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.reason = reason
        self.headers = {}

    def json(self):
        return self._payload


# Fixture shape from Consensus's own documented example response.
_DOCUMENTED_RESPONSE = {
    "results": [
        {
            "title": "The effects of creatine supplementation on cognitive performance",
            "authors": ["Sandkühler, J.F."],
            "publish_year": 2023,
            "doi": "10.1186/s12916-023-03146-5",
            "journal_name": "BMC Medicine",
            "citation_count": 47,
            "study_type": "rct",
            "sample_size": 123,
            "sjr_best_quartile": 1,
            "takeaway": "Creatine supplementation showed small positive effects on cognitive performance.",
            "abstract": "...",
            "url": "https://consensus.app/papers/example",
        }
    ],
    "page": 0,
    "page_size": 20,
    "is_end": False,
    "next_page": 1,
}


@pytest.mark.unit
def test_requires_query():
    tool = ConsensusTool({"name": "Consensus_search_papers"})
    result = tool.run({})
    assert result["status"] == "error"
    assert "query" in result["error"]


@pytest.mark.unit
def test_missing_api_key_returns_clear_error(monkeypatch):
    monkeypatch.delenv("CONSENSUS_API_KEY", raising=False)
    tool = ConsensusTool({"name": "Consensus_search_papers"})
    result = tool.run({"query": "creatine cognition"})
    assert result["status"] == "error"
    assert "CONSENSUS_API_KEY" in result["error"]


@pytest.mark.unit
def test_successful_search_returns_documented_shape(monkeypatch):
    monkeypatch.setenv("CONSENSUS_API_KEY", "test-key")
    tool = ConsensusTool({"name": "Consensus_search_papers"})

    captured = {}

    def fake_request_with_retry(
        session, method, url, *, params=None, headers=None, **kwargs
    ):
        captured["method"] = method
        captured["url"] = url
        captured["params"] = params
        captured["headers"] = headers
        return _FakeResponse(status_code=200, payload=_DOCUMENTED_RESPONSE)

    monkeypatch.setattr(
        "tooluniverse.consensus_tool.request_with_retry", fake_request_with_retry
    )

    result = tool.run({"query": "Does creatine improve cognition?"})

    assert captured["method"] == "GET"
    assert captured["url"] == "https://api.consensus.app/v1/search"
    assert captured["params"]["query"] == "Does creatine improve cognition?"
    assert captured["headers"]["x-api-key"] == "test-key"

    assert result["status"] == "success"
    assert result["data"] == _DOCUMENTED_RESPONSE["results"]
    assert result["metadata"]["returned"] == 1
    assert result["metadata"]["next_page"] == 1
    assert result["metadata"]["is_end"] is False


@pytest.mark.unit
def test_boolean_and_passthrough_filters_are_forwarded(monkeypatch):
    monkeypatch.setenv("CONSENSUS_API_KEY", "test-key")
    tool = ConsensusTool({"name": "Consensus_search_papers"})

    captured = {}

    def fake_request_with_retry(session, method, url, *, params=None, **kwargs):
        captured["params"] = params
        return _FakeResponse(status_code=200, payload={"results": []})

    monkeypatch.setattr(
        "tooluniverse.consensus_tool.request_with_retry", fake_request_with_retry
    )

    tool.run(
        {
            "query": "x",
            "human": True,
            "exclude_preprints": False,
            "year_min": 2015,
            "study_types": "rct,meta-analysis",
            "sjr_min": 1,
        }
    )

    assert captured["params"]["human"] == "true"
    assert captured["params"]["exclude_preprints"] == "false"
    assert captured["params"]["year_min"] == 2015
    assert captured["params"]["study_types"] == "rct,meta-analysis"
    assert captured["params"]["sjr_min"] == 1
    # Unset optional filters are omitted, not sent as null/None.
    assert "domain" not in captured["params"]
    assert "page" not in captured["params"]


@pytest.mark.unit
def test_unauthenticated_response_returns_clear_error(monkeypatch):
    monkeypatch.setenv("CONSENSUS_API_KEY", "wrong-key")
    tool = ConsensusTool({"name": "Consensus_search_papers"})

    def fake_request_with_retry(*args, **kwargs):
        return _FakeResponse(status_code=401, reason="Unauthorized")

    monkeypatch.setattr(
        "tooluniverse.consensus_tool.request_with_retry", fake_request_with_retry
    )

    result = tool.run({"query": "x"})
    assert result["status"] == "error"
    assert "401" in result["error"] or "authenticat" in result["error"].lower()


@pytest.mark.unit
def test_server_error_is_marked_retryable(monkeypatch):
    monkeypatch.setenv("CONSENSUS_API_KEY", "test-key")
    tool = ConsensusTool({"name": "Consensus_search_papers"})

    def fake_request_with_retry(*args, **kwargs):
        return _FakeResponse(status_code=503, reason="Service Unavailable")

    monkeypatch.setattr(
        "tooluniverse.consensus_tool.request_with_retry", fake_request_with_retry
    )

    result = tool.run({"query": "x"})
    assert result["status"] == "error"
    assert result["retryable"] is True
