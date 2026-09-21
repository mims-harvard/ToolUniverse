"""DisProt_search returned the same unfiltered first page for every query.

The tool sent ``q=<query>``, which DisProt's /search endpoint ignores (it answered
with all 3337 entries whatever the text), so searching ``TP53`` listed a
DNA-binding protein from adenovirus first. The query must be sent as one of the
filters DisProt does honour: ``disprot_id``, ``acc``, ``gene``, ``name`` or
``organism``.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.disprot_tool import DisProtTool

pytestmark = pytest.mark.unit


def _entry(acc, gene, name="protein"):
    return {
        "disprot_id": "DP" + acc[-5:].rjust(5, "0"),
        "acc": acc,
        "name": name,
        "genes": [{"name": {"value": gene}}],
        "organism": "Homo sapiens",
    }


class _Resp:
    def __init__(self, entries, size=None):
        self._body = {"data": entries, "size": len(entries) if size is None else size}

    def raise_for_status(self):
        pass

    def json(self):
        return self._body


def _search(query, responses, **extra):
    """Run a search; ``responses`` maps the filter name to the entries it returns."""
    calls = []

    def fake_get(url, params=None, timeout=None):
        (field,) = [k for k in params if k not in ("release", "page_size")]
        calls.append((field, params[field]))
        return _Resp(responses.get(field, []))

    tool = DisProtTool({"name": "DisProt_search", "fields": {"endpoint": "search"}})
    with patch("tooluniverse.disprot_tool.requests.get", side_effect=fake_get):
        result = tool.run({"query": query, **extra})
    return result, calls


def test_gene_symbol_is_sent_as_a_gene_and_name_filter_never_as_q():
    result, calls = _search("TP53", {"gene": [_entry("P04637", "TP53")]})
    assert [c[0] for c in calls] == ["gene", "name"]
    assert all(field != "q" for field, _ in calls)
    assert result["data"][0]["acc"] == "P04637"
    assert result["data"][0]["matched_on"] == "gene"


def test_gene_hits_come_first_and_name_hits_are_not_duplicated():
    result, _ = _search(
        "p53",
        {
            "gene": [_entry("P04637", "TP53")],
            "name": [_entry("P04637", "TP53"), _entry("O43715", "TRIAP1")],
        },
    )
    assert [e["acc"] for e in result["data"]] == ["P04637", "O43715"]


def test_disprot_id_and_uniprot_accession_use_exact_filters():
    _, calls = _search("dp00086", {"disprot_id": [_entry("P04637", "TP53")]})
    assert calls == [("disprot_id", "DP00086")]
    _, calls = _search("p04637", {"acc": [_entry("P04637", "TP53")]})
    assert calls == [("acc", "P04637")]


def test_organism_is_only_a_fallback_when_gene_and_name_match_nothing():
    result, calls = _search("Saccharomyces", {"organism": [_entry("P32774", "TOA2")]})
    assert [c[0] for c in calls] == ["gene", "name", "organism"]
    assert result["data"][0]["matched_on"] == "organism"
    _, calls = _search("kinase", {"name": [_entry("P61926", "PRKAR1A")]})
    assert [c[0] for c in calls] == ["gene", "name"]


def test_unsupported_keyword_returns_no_entries_instead_of_unrelated_ones():
    result, _ = _search("phase separation", {})
    assert result["status"] == "success"
    assert result["data"] == []
    assert result["metadata"]["total_matches_by_filter"] == {
        "gene": 0,
        "name": 0,
        "organism": 0,
    }


def test_page_size_caps_the_merged_list():
    genes = [_entry(f"P{i:05d}", f"G{i}") for i in range(30)]
    result, _ = _search("g", {"gene": genes}, page_size=5)
    assert len(result["data"]) == 5
    assert result["metadata"]["returned"] == 5


def test_empty_query_is_an_error():
    result, calls = _search("  ", {})
    assert result["status"] == "error" and calls == []
