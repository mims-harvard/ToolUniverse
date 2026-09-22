"""Tool_Finder_Jev: wide lexical retrieval, then graded relevance scoring.

Retrieval is deterministic and runs offline, so it is tested directly. Grading is one
HTTP call, so it is stubbed: what matters is that the tool sorts by the graded score,
falls back to retrieval order on ties, and reports a missing key instead of raising.
"""

import json
from unittest.mock import patch

import pytest

from tooluniverse.tool_finder_jev import ToolFinderJev, _BM25, _tokenize

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
        "parameter": {"type": "object", "properties": {"uniprot_id": {"type": "string"}}},
    },
    {
        "name": "FDA_get_drug_label",
        "description": "Return the printed label text for an approved drug product.",
        "parameter": {"type": "object", "properties": {"drug_name": {"type": "string"}}},
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
        picked = finder._search("predict the structure of a protein sequence", 2)

    assert picked[0] == "AlphaFold_get_prediction"


def test_equal_scores_keep_the_retrieval_order():
    finder = _finder()
    with _graded({t["name"]: 1.0 for t in CATALOGUE}):
        picked = finder._search("predict the structure of a protein sequence", 4)

    finder._ensure_index(finder._catalogue())
    assert picked == finder._retrieve("predict the structure of a protein sequence", 4)[:4]


def test_run_returns_tool_names_and_prompts():
    finder = _finder()
    with _graded({"ESMFold_predict_structure": 2.0}):
        out = finder.run({"description": "predict a protein structure", "limit": 2})

    assert out["tools"][0] == "ESMFold_predict_structure"
    assert out["tool_prompts"][0]["name"] == "ESMFold_predict_structure"
    assert out["candidate_depth"] == finder.candidate_depth


def test_missing_api_key_is_reported_not_raised(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    finder = _finder()

    out = finder.run({"description": "predict a protein structure"})

    assert "TYPESAFE_API_KEY" in out["error"]


def test_picked_tool_names_skip_retrieval_and_grading():
    finder = _finder()
    # No stub: if this reached the grading call it would need a key and a network.
    out = finder.run(
        {"description": "unused", "picked_tool_names": ["FDA_get_drug_label"], "limit": 5}
    )

    assert out["tools"] == ["FDA_get_drug_label"]
