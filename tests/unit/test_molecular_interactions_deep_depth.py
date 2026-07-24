"""molecular-interactions-deep depth tools: parse + error-path coverage (mocked HTTP).

Covers one new tool that closes a confirmed capability gap in OmniPath:

* ``OmniPath_get_annotation_resource_geneset`` (OmniPathTool, endpoint
  ``annotation_resource_geneset``) — resource-wide reverse annotation lookup.
  Retrieves the ENTIRE annotated gene/protein set for an OmniPath annotation
  resource (e.g. CancerGeneCensus driver genes, Surfaceome cell-surface
  proteins, kinase.com kinases) by calling ``/annotations?resources=<X>`` with
  NO ``proteins`` filter. The pre-existing annotations tool hard-requires a
  ``proteins`` argument, so this gene-set retrieval was previously unreachable.

All network calls are mocked; these tests never touch the live OmniPath API.
"""

import unittest
from unittest.mock import patch, MagicMock

import pytest

pytestmark = pytest.mark.unit


def _geneset_tool():
    """Instantiate OmniPathTool wired to the resource-geneset endpoint."""
    from tooluniverse.omnipath_tool import OmniPathTool

    return OmniPathTool(
        {
            "name": "OmniPath_get_annotation_resource_geneset",
            "timeout": 30,
            "fields": {"endpoint": "annotation_resource_geneset"},
        }
    )


def _mock_response(json_payload, content_type="application/json"):
    """Build a fake requests.Response-like object."""
    resp = MagicMock()
    resp.headers = {"content-type": content_type}
    resp.json.return_value = json_payload
    resp.raise_for_status.return_value = None
    return resp


# OmniPath returns long-format rows: one label/value pair per row, multiple
# rows per protein. KRAS has two annotation rows here (tier + hallmark).
_CGC_FAKE_ROWS = [
    {
        "uniprot": "P01116",
        "genesymbol": "KRAS",
        "entity_type": "protein",
        "source": "CancerGeneCensus",
        "label": "tier",
        "value": "1",
        "record_id": 370,
    },
    {
        "uniprot": "P01116",
        "genesymbol": "KRAS",
        "entity_type": "protein",
        "source": "CancerGeneCensus",
        "label": "hallmark",
        "value": "True",
        "record_id": 371,
    },
    {
        "uniprot": "P15056",
        "genesymbol": "BRAF",
        "entity_type": "protein",
        "source": "CancerGeneCensus",
        "label": "tier",
        "value": "1",
        "record_id": 99,
    },
]


class TestAnnotationResourceGenesetParse(unittest.TestCase):
    def test_groups_long_format_rows_per_protein(self):
        """Long-format label/value rows are grouped into one member per protein."""
        tool = _geneset_tool()
        with patch("tooluniverse.omnipath_tool.requests.get") as http:
            http.return_value = _mock_response(_CGC_FAKE_ROWS)
            result = tool.run({"resource": "CancerGeneCensus"})

        self.assertEqual(result["status"], "success")
        meta = result["metadata"]
        self.assertEqual(meta["resource"], "CancerGeneCensus")
        # Two unique proteins from three long-format rows.
        self.assertEqual(meta["total_members"], 2)
        self.assertEqual(meta["total_records"], 3)

        by_gene = {m["genesymbol"]: m for m in result["data"]}
        self.assertIn("KRAS", by_gene)
        kras = by_gene["KRAS"]
        self.assertEqual(kras["uniprot"], "P01116")
        self.assertEqual(kras["entity_type"], "protein")
        # Both label/value pairs collapsed into the annotations map.
        self.assertEqual(kras["annotations"]["tier"], "1")
        self.assertEqual(kras["annotations"]["hallmark"], "True")
        self.assertEqual(by_gene["BRAF"]["annotations"]["tier"], "1")

    def test_resources_param_sent_without_proteins_filter(self):
        """The API call uses resources=<X> and never sends a proteins filter."""
        tool = _geneset_tool()
        with patch("tooluniverse.omnipath_tool.requests.get") as http:
            http.return_value = _mock_response(_CGC_FAKE_ROWS)
            tool.run({"resource": "Surfaceome"})

        self.assertEqual(http.call_count, 1)
        _, called_kwargs = http.call_args
        params = called_kwargs["params"]
        self.assertEqual(params["resources"], "Surfaceome")
        self.assertEqual(params["format"], "json")
        self.assertNotIn("proteins", params)

    def test_resources_alias_accepted(self):
        """The plural 'resources' argument is accepted as an alias for 'resource'."""
        tool = _geneset_tool()
        with patch("tooluniverse.omnipath_tool.requests.get") as http:
            http.return_value = _mock_response(_CGC_FAKE_ROWS)
            result = tool.run({"resources": "CancerGeneCensus"})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["metadata"]["total_members"], 2)

    def test_entity_types_filter_forwarded(self):
        """Optional entity_types argument is forwarded to the API params."""
        tool = _geneset_tool()
        with patch("tooluniverse.omnipath_tool.requests.get") as http:
            http.return_value = _mock_response(_CGC_FAKE_ROWS)
            tool.run({"resource": "TFcensus", "entity_types": "protein"})
        _, called_kwargs = http.call_args
        self.assertEqual(called_kwargs["params"]["entity_types"], "protein")

    def test_empty_resource_returns_helpful_note(self):
        """An unknown resource yields an empty array -> success with a note."""
        tool = _geneset_tool()
        with patch("tooluniverse.omnipath_tool.requests.get") as http:
            http.return_value = _mock_response([])
            result = tool.run({"resource": "NotARealResource123"})

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"], [])
        self.assertEqual(result["metadata"]["total_members"], 0)
        self.assertIn("note", result["metadata"])


class TestAnnotationResourceGenesetErrors(unittest.TestCase):
    def test_missing_resource_argument_errors(self):
        """No resource argument -> structured error, no network call."""
        tool = _geneset_tool()
        with patch("tooluniverse.omnipath_tool.requests.get") as http:
            result = tool.run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("resource", result["error"].lower())
        http.assert_not_called()

    def test_network_error_returns_structured_error(self):
        """A requests exception is caught and returned as a structured error."""
        import requests

        tool = _geneset_tool()
        with patch("tooluniverse.omnipath_tool.requests.get") as http:
            http.side_effect = requests.exceptions.ConnectionError("boom")
            result = tool.run({"resource": "CancerGeneCensus"})
        self.assertEqual(result["status"], "error")
        self.assertIn("connect", result["error"].lower())

    def test_unexpected_payload_shape_errors(self):
        """A non-list JSON payload is reported as an error, never raised."""
        tool = _geneset_tool()
        with patch("tooluniverse.omnipath_tool.requests.get") as http:
            http.return_value = _mock_response({"unexpected": "dict"})
            result = tool.run({"resource": "CancerGeneCensus"})
        self.assertEqual(result["status"], "error")
        self.assertIn("Unexpected response format", result["error"])


if __name__ == "__main__":
    unittest.main()
