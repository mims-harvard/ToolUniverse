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

    def test_gene_search_requests_enough_leading_matches_for_offset_page(self):
        tool = _make_tool("gene_search")
        matches = [
            {
                "gene": {
                    "geneId": f"GENE{index}",
                    "species": {"id": 9606},
                }
            }
            for index in range(7)
        ]
        with patch("tooluniverse.bgee_tool.requests.get") as get:
            resp = MagicMock()
            resp.raise_for_status.return_value = None
            resp.json.return_value = {
                "code": 200,
                "data": {"result": {"geneMatches": matches, "totalMatchCount": 20_000}},
            }
            get.return_value = resp
            result = tool.run(
                {
                    "query": "kinase",
                    "species_id": "9606",
                    "limit": 2,
                    "offset": 5,
                }
            )

        params = get.call_args.kwargs["params"]
        self.assertEqual(params["limit"], 7)
        self.assertEqual(params["species_id"], "9606")
        self.assertEqual(
            [item["gene_id"] for item in result["data"]], ["GENE5", "GENE6"]
        )
        self.assertEqual(result["metadata"]["accessible_matches"], 10_000)
        self.assertTrue(result["metadata"]["upstream_truncated"])
        self.assertEqual(result["metadata"]["next_offset"], 7)

    def test_gene_expression_exposes_later_calls(self):
        tool = _make_tool("gene_expression")
        calls = [
            {
                "condition": {
                    "anatEntity": {"id": f"UBERON:{index}", "name": f"Tissue {index}"}
                },
                "expressionScore": {},
            }
            for index in range(5)
        ]
        with patch("tooluniverse.bgee_tool.requests.get") as get:
            resp = MagicMock()
            resp.raise_for_status.return_value = None
            resp.json.return_value = {"code": 200, "data": {"calls": calls}}
            get.return_value = resp
            result = tool.run(
                {
                    "gene_id": "ENSG00000141510",
                    "species_id": "9606",
                    "limit": 2,
                    "offset": 2,
                }
            )

        self.assertEqual(
            [item["tissue_name"] for item in result["data"]],
            ["Tissue 2", "Tissue 3"],
        )
        self.assertEqual(result["metadata"]["next_offset"], 4)

    def test_gene_search_rejects_coerced_or_out_of_range_pagination(self):
        tool = _make_tool("gene_search")
        invalid = (
            {"query": "TP53", "limit": "2"},
            {"query": "TP53", "limit": True},
            {"query": "TP53", "limit": 0},
            {"query": "TP53", "offset": -1},
            {"query": "TP53", "offset": 10_000},
        )
        with patch("tooluniverse.bgee_tool.requests.get") as get:
            for arguments in invalid:
                result = tool.run(arguments)
                self.assertEqual(result["status"], "error", arguments)
        get.assert_not_called()

    def test_gene_expression_rejects_malformed_pagination(self):
        tool = _make_tool("gene_expression")
        required = {"gene_id": "ENSG00000141510", "species_id": "9606"}
        with patch("tooluniverse.bgee_tool.requests.get") as get:
            for pagination in ({"limit": 501}, {"offset": "2"}, {"offset": False}):
                result = tool.run({**required, **pagination})
                self.assertEqual(result["status"], "error", pagination)
        get.assert_not_called()


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
