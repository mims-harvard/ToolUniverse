"""Regression tests for enrichr_gene_enrichment_analysis input/output handling.

Two confirmed defects in the freshly-wrapped 1.4.0 tool:

* An explicit empty ``libs`` list (which is the tool's own documented example,
  ``{"gene_list": [...], "libs": []}``) queried zero libraries and returned an
  empty enrichment wrapped in ``status: success`` -- the "valid input silently
  returns empty as success" class. Empty/omitted ``libs`` must fall back to the
  default library set.
* ``data`` was a double-JSON-encoded string (``json.dumps(result)``), forcing
  every consumer to ``json.loads`` a second time, inconsistent with every other
  ToolUniverse tool. ``data`` must be a structured object.

These are unit-level (``run`` logic) and mock out the network via ``enrichr_api``.
"""

import unittest
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit


def _tool():
    from tooluniverse.enrichr_tool import EnrichrTool

    return EnrichrTool(
        {"name": "enrichr_gene_enrichment_analysis", "type": "EnrichrTool"}
    )


_FAKE_RESULT = (
    {"Path: ['TP53', 'term', 'BRCA1']": "Total Weight: 12.0"},
    {"Connectivity: TP53 - term": [[["TP53", "term"], 1]]},
)


class TestEnrichrLibsFallback(unittest.TestCase):
    def test_empty_libs_falls_back_to_default(self):
        """libs=[] must query the default library set, not zero libraries."""
        from tooluniverse.enrichr_tool import EnrichrTool

        tool = _tool()
        with patch.object(
            type(tool), "enrichr_api", return_value=_FAKE_RESULT
        ) as api:
            tool.run({"gene_list": ["TP53", "BRCA1"], "libs": []})
        called_libs = api.call_args.args[1]
        self.assertEqual(called_libs, EnrichrTool.DEFAULT_LIBS)

    def test_omitted_libs_falls_back_to_default(self):
        """Omitting libs also uses the default set."""
        from tooluniverse.enrichr_tool import EnrichrTool

        tool = _tool()
        with patch.object(
            type(tool), "enrichr_api", return_value=_FAKE_RESULT
        ) as api:
            tool.run({"gene_list": ["TP53", "BRCA1"]})
        self.assertEqual(api.call_args.args[1], EnrichrTool.DEFAULT_LIBS)

    def test_explicit_libs_used_verbatim(self):
        """A non-empty libs list is passed through unchanged."""
        tool = _tool()
        with patch.object(
            type(tool), "enrichr_api", return_value=_FAKE_RESULT
        ) as api:
            tool.run(
                {"gene_list": ["TP53", "BRCA1"], "libs": ["KEGG_2021_Human"]}
            )
        self.assertEqual(api.call_args.args[1], ["KEGG_2021_Human"])


class TestEnrichrOutputShape(unittest.TestCase):
    def test_data_is_structured_object_not_string(self):
        """data must be a dict with connected_paths/connections, not a JSON string."""
        tool = _tool()
        with patch.object(type(tool), "enrichr_api", return_value=_FAKE_RESULT):
            result = tool.run({"gene_list": ["TP53", "BRCA1"], "libs": ["X"]})
        self.assertEqual(result["status"], "success")
        data = result["data"]
        self.assertIsInstance(data, dict)
        self.assertIn("connected_paths", data)
        self.assertIn("connections", data)
        self.assertIsInstance(data["connected_paths"], dict)

    def test_metadata_reports_libraries_and_gene_count(self):
        """metadata surfaces the libraries queried and the gene count."""
        tool = _tool()
        with patch.object(type(tool), "enrichr_api", return_value=_FAKE_RESULT):
            result = tool.run(
                {"gene_list": ["TP53", "BRCA1"], "libs": ["KEGG_2021_Human"]}
            )
        meta = result["metadata"]
        self.assertEqual(meta["libraries"], ["KEGG_2021_Human"])
        self.assertEqual(meta["gene_count"], 2)


if __name__ == "__main__":
    unittest.main()
