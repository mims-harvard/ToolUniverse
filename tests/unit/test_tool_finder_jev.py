"""Tool_Finder_Jev: wide lexical retrieval, then graded relevance scoring.

Retrieval is deterministic and runs offline, so it is tested directly. Grading is one
HTTP call, so it is stubbed: what matters is that the tool sorts by the graded score,
falls back to retrieval order on ties, and reports a missing key instead of raising.
"""

import json
import urllib.error
from unittest.mock import patch

import pytest

from tooluniverse.tool_finder_jev import ENDPOINT, ToolFinderJev, _BM25, _tokenize

pytestmark = pytest.mark.unit


CATALOGUE = [
    {
        "name": "ESMFold_predict_structure",
        "description": "Predict the three-dimensional structure of a protein from its amino acid sequence.",
        "parameter": {"type": "object", "properties": {"sequence": {"type": "string"}}},
    },
    {
        "name": "AlphaFold_get_prediction",
        "description": "Retrieve a predicted protein structure model from the AlphaFold database.",
        "parameter": {
            "type": "object",
            "properties": {"uniprot_id": {"type": "string"}},
        },
    },
    {
        "name": "FDA_get_drug_label",
        "description": "Return the printed label text for an approved drug product.",
        "parameter": {
            "type": "object",
            "properties": {"drug_name": {"type": "string"}},
        },
    },
    {
        "name": "Weather_get_forecast",
        "description": "Return the weather forecast for a location.",
        "parameter": {"type": "object", "properties": {"city": {"type": "string"}}},
    },
]


class _FakeUniverse:
    def __init__(self, tools):
        self.all_tools = list(tools)
        self.all_tool_dict = {t["name"]: t for t in tools}

    def return_all_loaded_tools(self, copy_tools=True):
        return list(self.all_tools)

    def get_tool_specification_by_names(self, names):
        return [self.all_tool_dict[n] for n in names if n in self.all_tool_dict]

    def prepare_tool_prompts(self, tools):
        return [{"name": t["name"], "description": t["description"]} for t in tools]


def _finder(**configs):
    return ToolFinderJev({"configs": configs}, tooluniverse=_FakeUniverse(CATALOGUE))


# ----------------------------------------------------------------- tokenisation
def test_tokenizer_drops_stopwords_and_schema_vocabulary():
    tokens = _tokenize(json.dumps(CATALOGUE[0]))

    assert "esmfold" in tokens and "structure" in tokens
    # The document is a JSON dump, so without filtering these would be indexed and
    # would appear in nearly every tool.
    for noise in ("type", "properties", "object", "string", "name", "description"):
        assert noise not in tokens
    assert "the" not in tokens and "from" not in tokens


# ----------------------------------------------------------------- retrieval
def test_bm25_ranks_the_matching_document_first():
    docs = [_tokenize(json.dumps(t)) for t in CATALOGUE]
    index = _BM25(docs)

    top = index.top(_tokenize("predict protein structure from sequence"), 2)

    assert top[0] == 0  # ESMFold


def test_retrieval_is_offline_and_orders_by_relevance():
    finder = _finder()
    tools = finder._catalogue()
    finder._ensure_index(tools)

    names = finder._retrieve("predict the structure of a protein sequence", 4)

    assert names[0] == "ESMFold_predict_structure"
    assert "Weather_get_forecast" in names  # a wide shortlist keeps weak candidates


def test_index_is_reused_until_the_tool_set_changes():
    finder = _finder()
    tools = finder._catalogue()
    finder._ensure_index(tools)
    first = finder._index

    finder._ensure_index(tools)
    assert finder._index is first

    finder._ensure_index(tools[:2])
    assert finder._index is not first


# ----------------------------------------------------------------- grading
def _graded(scores):
    """Stub the one HTTP call with a fixed score per candidate, in order."""

    def fake(self, query, candidates, descriptions):
        return [scores.get(name, 0.0) for name in candidates]

    return patch.object(ToolFinderJev, "_grade", fake)


def test_results_are_ordered_by_the_graded_score_not_by_retrieval():
    finder = _finder()
    # Retrieval puts ESMFold first; grading disagrees.
    scores = {"ESMFold_predict_structure": 0.2, "AlphaFold_get_prediction": 2.0}

    with _graded(scores):
        picked, grading_error = finder._search(
            "predict the structure of a protein sequence", 2
        )

    assert picked[0] == "AlphaFold_get_prediction"
    assert grading_error is None


def test_equal_scores_keep_the_retrieval_order():
    finder = _finder()
    with _graded({t["name"]: 1.0 for t in CATALOGUE}):
        picked, _ = finder._search("predict the structure of a protein sequence", 4)

    finder._ensure_index(finder._catalogue())
    assert (
        picked == finder._retrieve("predict the structure of a protein sequence", 4)[:4]
    )


def test_run_returns_tool_names_and_prompts():
    finder = _finder()
    with _graded({"ESMFold_predict_structure": 2.0}):
        out = finder.run({"description": "predict a protein structure", "limit": 2})

    assert out["tools"][0] == "ESMFold_predict_structure"
    assert out["tool_prompts"][0]["name"] == "ESMFold_predict_structure"
    assert out["candidate_depth"] == finder.candidate_depth
    assert out["graded"] is True
    # Every search that reaches the grader says where the query went.
    assert "api.typesafe.ai" in out["provider_notice"]


def test_missing_api_key_is_reported_not_raised(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    finder = _finder()

    out = finder.run({"description": "predict a protein structure"})

    assert "TYPESAFE_API_KEY" in out["error"]


def test_picked_tool_names_skip_retrieval_and_grading():
    finder = _finder()
    # No stub: if this reached the grading call it would need a key and a network.
    out = finder.run(
        {
            "description": "unused",
            "picked_tool_names": ["FDA_get_drug_label"],
            "limit": 5,
        }
    )

    assert out["tools"] == ["FDA_get_drug_label"]


# ----------------------------------------------------------- provider failure
def _grade_raises(exc):
    def fake(self, query, candidates, descriptions):
        raise exc

    return patch.object(ToolFinderJev, "_grade", fake)


def test_grading_outage_returns_the_retrieval_order_instead_of_an_error():
    """A provider outage degrades the ranking; it does not lose the shortlist.

    BM25 has already produced usable candidates by the time grading runs, and every
    other finder answers with something, so returning an error here would leave the
    caller with no tools over a failure on the far side of one HTTP call.
    """
    finder = _finder()
    query = "predict the structure of a protein sequence"
    error = urllib.error.HTTPError(ENDPOINT, 503, "Service Unavailable", {}, None)

    with _grade_raises(error):
        out = finder.run({"description": query, "limit": 3})

    finder._ensure_index(finder._catalogue())
    assert out["tools"] == finder._retrieve(query, finder.candidate_depth)[:3]
    assert out["graded"] is False
    assert "503" in out["grading_error"]
    assert "retrieval order" in out["note"]
    assert "api.typesafe.ai" in out["provider_notice"]


def test_a_transport_failure_degrades_the_same_way():
    finder = _finder()
    with _grade_raises(urllib.error.URLError("connection refused")):
        out = finder.run({"description": "predict a protein structure", "limit": 2})

    assert out["tools"]
    assert out["graded"] is False
    assert "connection refused" in out["grading_error"]


def test_a_missing_key_is_not_treated_as_an_outage(monkeypatch):
    """A credential the deployment never set is a configuration error, not an outage:
    silently returning ungraded results would hide it for the life of the process."""
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    finder = _finder()

    out = finder.run({"description": "predict a protein structure", "limit": 2})

    assert "TYPESAFE_API_KEY" in out["error"]
    assert "tools" not in out


def test_picked_tool_names_do_not_claim_a_provider_call():
    """Nothing was sent anywhere, so nothing is disclosed."""
    finder = _finder()
    out = finder.run(
        {"description": "unused", "picked_tool_names": ["FDA_get_drug_label"]}
    )

    assert "provider_notice" not in out
    assert "graded" not in out
