"""Bgee requests must target ``https://www.bgee.org/api/`` (with trailing slash).

Regression: the tool built its URL from ``https://www.bgee.org/api`` (no
trailing slash).  Requests to that path never reach the Bgee application -- the
site's Cloudflare WAF answers them with an HTTP 403 challenge page
(``cf-mitigated: challenge``), so every Bgee tool, including the documented
``Bgee_get_gene_expression`` example (ENSG00000141510 / 9606), returned
"Bgee API HTTP error: 403".  The same query with the trailing slash returns
HTTP 200 and 145 expression calls.  Bisection showed this is independent of
User-Agent (python-requests, curl and a browser UA all 403 without the slash
and all 200 with it) and of the Accept header.

Also covers the error path: Bgee reports an unknown gene ID as HTTP 404 with a
JSON body carrying a ``message``, which must be surfaced instead of a bare
status code.
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest
import requests

pytestmark = pytest.mark.unit


def _make_tool(endpoint):
    from tooluniverse.bgee_tool import BgeeTool

    return BgeeTool(
        {
            "name": f"Bgee_{endpoint}",
            "type": "BgeeTool",
            "fields": {"endpoint": endpoint},
        }
    )


class TestBgeeBaseUrl(unittest.TestCase):
    def test_module_base_url_has_trailing_slash(self):
        import tooluniverse.bgee_tool as mod

        self.assertEqual(mod.BGEE_BASE_URL, "https://www.bgee.org/api/")
        self.assertTrue(mod.BGEE_BASE_URL.endswith("/"))

    def test_gene_expression_request_uses_trailing_slash(self):
        tool = _make_tool("gene_expression")
        with patch("tooluniverse.bgee_tool.requests.get") as get:
            resp = MagicMock()
            resp.raise_for_status.return_value = None
            resp.json.return_value = {
                "code": 200,
                "status": "SUCCESS",
                "data": {
                    "requestedDataTypes": ["RNA-Seq"],
                    "calls": [
                        {
                            "condition": {
                                "anatEntity": {
                                    "id": "UBERON:0003053",
                                    "name": "ventricular zone",
                                }
                            },
                            "expressionScore": {
                                "expressionScore": "95.11",
                                "expressionScoreConfidence": "high",
                            },
                            "expressionState": "expressed",
                            "expressionQuality": "gold",
                            "dataTypesWithData": ["RNA-Seq"],
                        }
                    ],
                },
            }
            get.return_value = resp
            result = tool.run({"gene_id": "ENSG00000141510", "species_id": "9606"})

        url = get.call_args.args[0]
        self.assertEqual(url, "https://www.bgee.org/api/")
        self.assertTrue(
            url.endswith("/"),
            "Bgee URL must keep its trailing slash or Cloudflare returns 403",
        )
        self.assertEqual(
            get.call_args.kwargs["params"],
            {
                "page": "gene",
                "action": "expression",
                "gene_id": "ENSG00000141510",
                "species_id": "9606",
                "display_type": "json",
            },
        )
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"][0]["tissue_name"], "ventricular zone")

    def test_all_endpoints_use_trailing_slash(self):
        cases = {
            "gene_search": {"query": "TP53"},
            "gene_expression": {"gene_id": "ENSG00000141510", "species_id": "9606"},
            "species_list": {},
        }
        for endpoint, args in cases.items():
            with self.subTest(endpoint=endpoint):
                tool = _make_tool(endpoint)
                with patch("tooluniverse.bgee_tool.requests.get") as get:
                    resp = MagicMock()
                    resp.raise_for_status.return_value = None
                    resp.json.return_value = {"code": 200, "data": {}}
                    get.return_value = resp
                    tool.run(args)
                self.assertEqual(get.call_args.args[0], "https://www.bgee.org/api/")


class TestBgeeHttpErrorMessage(unittest.TestCase):
    def test_unknown_gene_404_surfaces_api_message(self):
        tool = _make_tool("gene_expression")
        with patch("tooluniverse.bgee_tool.requests.get") as get:
            resp = MagicMock()
            resp.status_code = 404
            resp.json.return_value = {
                "code": 404,
                "status": "ERROR",
                "message": "Page not found.",
                "data": {"exceptionType": "PageNotFoundException"},
            }
            resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
                response=resp
            )
            get.return_value = resp
            result = tool.run({"gene_id": "ENSG99999999999", "species_id": "9606"})

        self.assertEqual(result["status"], "error")
        self.assertIn("404", result["error"])
        self.assertIn("Page not found.", result["error"])
        self.assertIn("Ensembl", result["error"])

    def test_http_error_without_json_body_still_reports_status(self):
        tool = _make_tool("species_list")
        with patch("tooluniverse.bgee_tool.requests.get") as get:
            resp = MagicMock()
            resp.status_code = 500
            resp.json.side_effect = ValueError("no json")
            resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
                response=resp
            )
            get.return_value = resp
            result = tool.run({})

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error"], "Bgee API HTTP error: 500")


if __name__ == "__main__":
    unittest.main()
