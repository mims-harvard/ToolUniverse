"""Regression guard for Fix-R9C-1: PubMedRESTTool._build_params passed a
query's hyphens straight through to NCBI's esearch `term` param. NCBI's
automatic term-mapping treats a hyphenated compound (e.g. "CYP3A5-guided")
as a literal [All Fields] phrase rather than decomposing it into
individual words, which silently zeroed out an otherwise-matching
multi-keyword AND query (confirmed live: 0 results for "CYP3A5-guided
tacrolimus dosing kidney transplant" vs. 38 with the hyphen replaced by a
space). Hyphens are now replaced with spaces before building the query.
"""

import pytest

from tooluniverse.pubmed_tool import PubMedRESTTool

pytestmark = pytest.mark.unit


def _tool():
    return PubMedRESTTool(
        {
            "name": "PubMed_search_articles",
            "fields": {
                "endpoint": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                "db": "pubmed",
                "retmode": "json",
            },
        }
    )


def test_hyphenated_compound_term_is_space_normalized():
    tool = _tool()
    params = tool._build_params(
        {"query": "CYP3A5-guided tacrolimus dosing kidney transplant"}
    )
    assert params["term"] == "CYP3A5 guided tacrolimus dosing kidney transplant"


def test_query_without_hyphens_unaffected():
    tool = _tool()
    params = tool._build_params({"query": "narcolepsy pharmacological treatment"})
    assert params["term"] == "narcolepsy pharmacological treatment"
