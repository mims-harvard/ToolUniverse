"""NCBI_search_nucleotide and NCBI_SRA_search_runs sorted by names NCBI ignores.

The tools forwarded ``sort`` verbatim. esearch answers an unknown schema with
"Unknown sort schema 'pub_date' ignored" and returns its default order, so pub_date and
title changed nothing (identical results for every value). nuccore's real schemas are
"Date Released" and "Sequence Length" (verified: both reorder the results); SRA has none.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tooluniverse.ncbi_nucleotide_tool import NCBINucleotideSearchTool
from tooluniverse.ncbi_sra_tool import NCBISRATool

pytestmark = pytest.mark.unit

DATA = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data"
EMPTY = {"status": "success", "data": {"esearchresult": {"idlist": [], "count": "0"}}}


def _config(filename, name):
    tools = json.loads((DATA / filename).read_text(encoding="utf-8"))
    return next(t for t in tools if t["name"] == name)


def _esearch_params(cls, config, arguments):
    tool = cls(config)
    with patch.object(tool, "_make_request", return_value=EMPTY) as request:
        tool.run(arguments)
    (endpoint, params), _ = request.call_args
    assert endpoint == "/esearch.fcgi"
    return params


NUC = _config("ncbi_nucleotide_tools.json", "NCBI_search_nucleotide")
NUC_ARGS = {"operation": "search", "organism": "Homo sapiens", "keywords": "insulin"}


@pytest.mark.parametrize(
    "sort,expected",
    [("pub_date", "Date Released"), ("length", "Sequence Length")],
)
def test_nucleotide_sort_is_sent_as_the_ncbi_schema_name(sort, expected):
    params = _esearch_params(NCBINucleotideSearchTool, NUC, {**NUC_ARGS, "sort": sort})
    assert params["sort"] == expected


def test_nucleotide_relevance_sends_no_sort_parameter():
    assert "sort" not in _esearch_params(NCBINucleotideSearchTool, NUC, NUC_ARGS)
    assert "sort" not in _esearch_params(
        NCBINucleotideSearchTool, NUC, {**NUC_ARGS, "sort": "relevance"}
    )


def test_nucleotide_offers_only_sorts_that_work():
    sort = NUC["parameter"]["properties"]["sort"]
    assert sort["enum"] == ["relevance", "pub_date", "length"]


def test_sra_never_sends_a_sort_and_offers_only_relevance():
    config = _config("ncbi_sra_tools.json", "NCBI_SRA_search_runs")
    params = _esearch_params(
        NCBISRATool,
        config,
        {"operation": "search", "organism": "Homo sapiens", "strategy": "RNA-Seq"},
    )
    assert "sort" not in params
    assert config["parameter"]["properties"]["sort"]["enum"] == ["relevance"]
