"""ProtVar_get_function tolerates null list fields in the UniProt payload.

Regression: a comment with an explicit ``"text": null`` (or a null
features/comments list) made the tool do ``for t in None`` -> TypeError, which
then surfaced as a confusing 'object has no attribute handle_error'. The tool
must treat null lists as empty.
"""

import unittest
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit


def _tool():
    from tooluniverse.protvar_tool import ProtVarFunctionTool

    return ProtVarFunctionTool(
        {"name": "ProtVar_get_function", "type": "ProtVarFunctionTool"}
    )


def _map_tool():
    from tooluniverse.protvar_tool import ProtVarMapTool

    return ProtVarMapTool({"name": "ProtVar_map_variant", "type": "ProtVarTool"})


class TestProtVarMapNewEndpoint(unittest.TestCase):
    # ProtVar 2.x serves GET /mapping?q=&assembly=, returning
    # content.inputs[].derivedGenomicVariants[].genes[].isoforms[].
    _RESPONSE = {
        "content": {
            "inputs": [
                {
                    "inputStr": "P04637 R175H",
                    "messages": [],
                    "derivedGenomicVariants": [
                        {
                            "chromosome": "17",
                            "position": 7675088,
                            "refBase": "C",
                            "altBase": "T",
                            "genes": [
                                {
                                    "geneName": "TP53",
                                    "ensg": "ENSG00000141510.19",
                                    "caddScore": 25.9,
                                    "isoforms": [
                                        {
                                            "accession": "P04637",
                                            "canonical": True,
                                            "consequences": "missense",
                                            "refAA": "Arg",
                                            "variantAA": "His",
                                            "amScore": {
                                                "amPathogenicity": 0.9857,
                                                "amClass": "PATHOGENIC",
                                            },
                                            "popEveScore": {"eve": 5.982, "esm1v": -7.744, "popeve": -3.658},
                                        }
                                    ],
                                }
                            ],
                        }
                    ],
                }
            ]
        }
    }

    def test_get_mapping_parsed(self):
        tool = _map_tool()
        with patch(
            "tooluniverse.protvar_tool._get_json", return_value=self._RESPONSE
        ) as get:
            result = tool.run({"variant": "P04637 R175H"})
        # uses the new GET /mapping?q=&assembly= contract
        called = get.call_args.args[0]
        self.assertIn("/mapping?", called)
        self.assertIn("q=", called)
        self.assertIn("assembly=GRCh38", called)
        self.assertEqual(result["status"], "success")
        d = result["data"]
        self.assertEqual(d["genomic_coordinates"]["chr"], "17")
        iso = d["isoform_mappings"][0]
        self.assertEqual(iso["gene"], "TP53")
        self.assertEqual(iso["alphamissense"]["class"], "PATHOGENIC")
        self.assertEqual(iso["cadd_score"], 25.9)
        self.assertEqual(iso["eve_score"], 5.982)

    def test_empty_inputs_is_clean_error(self):
        tool = _map_tool()
        with patch(
            "tooluniverse.protvar_tool._get_json", return_value={"content": {"inputs": []}}
        ):
            result = tool.run({"variant": "not a variant"})
        self.assertEqual(result["status"], "error")
        self.assertIn("No mapping found", result["error"])


class TestProtVarNullFields(unittest.TestCase):
    def test_null_text_does_not_crash(self):
        tool = _tool()
        payload = {
            "accession": "P04637",
            "position": 175,
            "name": "Cellular tumor antigen p53",
            "features": None,  # explicit null list
            "comments": [
                {"type": "FUNCTION", "text": None},  # explicit null list
                {"type": "DISEASE", "text": [{"value": "Li-Fraumeni syndrome"}]},
            ],
        }
        with patch("tooluniverse.protvar_tool._get_json", return_value=payload):
            result = tool.run({"accession": "P04637", "position": 175})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["features"], [])
        self.assertEqual(
            result["data"]["comments"],
            [{"type": "DISEASE", "value": "Li-Fraumeni syndrome"}],
        )

    def test_non_dict_result_is_clean_error(self):
        tool = _tool()
        with patch("tooluniverse.protvar_tool._get_json", return_value=None):
            result = tool.run({"accession": "P04637", "position": 175})
        self.assertEqual(result["status"], "error")
        self.assertIn("No ProtVar function annotation", result["error"])


if __name__ == "__main__":
    unittest.main()
