"""Regression guard for Feature-26C-4: CPIC_search_gene_drug_pairs advertised a
provenance `url` that did not reproduce its own result.

The tool's PostgREST filters (`genesymbol=eq.HLA-B`, `cpiclevel=eq.A`, `limit`)
travel as request query params, but the reported `url` was the bare endpoint
template. Confirmed live that `{"gene": "HLA-B"}` (13 rows) and `{}` (635 rows)
returned a byte-identical url, and that pasting it returns all 635 rows -- so a
caller spot-checking provenance concludes the gene filter was ignored. The url
is now taken from the response requests actually issued, so it cannot drift
from the params used to build the request.
"""

import json
import unittest.mock as mock
from pathlib import Path

import pytest
import requests

from tooluniverse.cpic_search_pairs_tool import CPICSearchPairsTool

pytestmark = pytest.mark.unit

_DATA_DIR = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data"

_ROWS = [
    {"genesymbol": "HLA-B", "drugid": "RxNorm:190521", "cpiclevel": "A"},
    {"genesymbol": "HLA-B", "drugid": "RxNorm:2002", "cpiclevel": "A"},
]


def _tool_config(name):
    configs = json.loads((_DATA_DIR / "cpic_tools.json").read_text())
    for cfg in configs:
        if cfg["name"] == name:
            return cfg
    raise AssertionError(f"{name} not found in cpic_tools.json")


def _run(name, arguments):
    """Run the tool with the HTTP layer replaced, returning (result, sent_url).

    The fake response's `url` is built with requests' own preparation step, so
    it is exactly the URL a real request would have carried.
    """
    tool = CPICSearchPairsTool(_tool_config(name))
    sent = {}

    def fake_request(session, method, url, params=None, **kwargs):
        prepared = requests.Request(method, url, params=params).prepare()
        sent["url"] = prepared.url
        response = mock.MagicMock()
        response.status_code = 200
        response.url = prepared.url
        response.json.return_value = _ROWS
        response.text = json.dumps(_ROWS)
        response.headers = {"content-type": "application/json"}
        return response

    with mock.patch(
        "tooluniverse.base_rest_tool.request_with_retry", side_effect=fake_request
    ):
        result = tool.run(arguments)
    return result, sent["url"]


class TestReportedUrlIsTheRequestedUrl:
    def test_gene_filter_appears_in_reported_url(self):
        result, sent_url = _run("CPIC_search_gene_drug_pairs", {"gene": "HLA-B"})

        assert result["status"] == "success"
        assert result["url"] == sent_url
        assert "genesymbol=eq.HLA-B" in result["url"]

    def test_filtered_and_unfiltered_urls_differ(self):
        # The failure this guards: two different answers advertising the same
        # provenance url.
        filtered, _ = _run("CPIC_search_gene_drug_pairs", {"gene": "HLA-B"})
        unfiltered, _ = _run("CPIC_search_gene_drug_pairs", {})

        assert filtered["url"] != unfiltered["url"]
        assert "genesymbol=" not in unfiltered["url"]

    def test_level_and_limit_filters_appear_in_reported_url(self):
        result, sent_url = _run(
            "CPIC_search_gene_drug_pairs", {"cpiclevel": "A", "limit": 10}
        )

        assert result["url"] == sent_url
        assert "cpiclevel=eq.A" in result["url"]
        assert "limit=10" in result["url"]

    def test_select_clause_is_still_reported(self):
        result, _ = _run("CPIC_search_gene_drug_pairs", {"gene": "HLA-B"})

        assert "select=" in result["url"]

    def test_sibling_tool_on_the_same_class_also_reports_its_filter(self):
        result, sent_url = _run("CPIC_get_gene_drug_pairs", {"gene": "CYP2D6"})

        assert result["url"] == sent_url
        assert "genesymbol=eq.CYP2D6" in result["url"]
