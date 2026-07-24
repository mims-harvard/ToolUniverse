"""Chem / metabolomics depth tools (mocked HTTP, no live calls).

Covers the four new metabolite-identification / lipid tools that reuse existing
tool classes:
  - KEGG_find_compound            (KEGGExtTool, endpoint=find_compound)
  - metabolights_get_reference_compound (MetaboLightsRESTTool)
  - LipidMaps_get_compound_by_xref      (LipidMapsTool, context=compound)
  - SwissLipids_get_children            (SwissLipidsTool, operation=get_children)

Each tool gets a parse (success) test and an error-path test.
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


def _text_resp(status_code, text):
    r = MagicMock()
    r.status_code = status_code
    r.text = text
    r.raise_for_status = MagicMock()
    return r


def _json_resp(status_code, body, text=""):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = body
    r.text = text
    r.url = "https://example.test/url"
    r.raise_for_status = MagicMock()
    return r


# --------------------------------------------------------------------------- #
# KEGG_find_compound
# --------------------------------------------------------------------------- #
class TestKEGGFindCompound(unittest.TestCase):
    def _tool(self):
        from tooluniverse.kegg_ext_tool import KEGGExtTool

        return KEGGExtTool(
            {
                "name": "KEGG_find_compound",
                "type": "KEGGExtTool",
                "fields": {"endpoint": "find_compound"},
            }
        )

    def test_exact_mass_parses_candidate_ids(self):
        """Exact mass parses candidate ids."""
        body = (
            "C00493\t174.052823\n"
            "C04236\t174.052823\n"
            "C16588\t174.052823\n"
        )
        with patch("tooluniverse.kegg_ext_tool.requests.get") as get:
            get.return_value = _text_resp(200, body)
            result = self._tool().run({"exact_mass": "174.05"})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["search_field"], "exact_mass")
        self.assertEqual(result["data"]["count"], 3)
        ids = [c["compound_id"] for c in result["data"]["compounds"]]
        self.assertEqual(ids, ["C00493", "C04236", "C16588"])
        # exact_mass routed to the /exact_mass sub-path
        self.assertTrue(get.call_args.args[0].endswith("/find/compound/174.05/exact_mass"))

    def test_formula_routes_to_formula_path_and_strips_cpd_prefix(self):
        """Formula routes to formula path and strips cpd prefix."""
        body = "cpd:C00031\tC6H12O6\ncpd:C00095\tC6H12O6\n"
        with patch("tooluniverse.kegg_ext_tool.requests.get") as get:
            get.return_value = _text_resp(200, body)
            result = self._tool().run({"formula": "C6H12O6"})
        self.assertEqual(result["status"], "success")
        ids = [c["compound_id"] for c in result["data"]["compounds"]]
        self.assertEqual(ids, ["C00031", "C00095"])  # cpd: prefix stripped
        self.assertTrue(get.call_args.args[0].endswith("/find/compound/C6H12O6/formula"))

    def test_name_routes_to_plain_find_path(self):
        """Name routes to plain find path."""
        body = "C07481\tCaffeine; 1,3,7-Trimethylxanthine\n"
        with patch("tooluniverse.kegg_ext_tool.requests.get") as get:
            get.return_value = _text_resp(200, body)
            result = self._tool().run({"name": "caffeine"})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["compounds"][0]["compound_id"], "C07481")
        self.assertTrue(get.call_args.args[0].endswith("/find/compound/caffeine"))

    def test_no_field_is_error(self):
        """No field is error."""
        result = self._tool().run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("required", result["error"])

    def test_multiple_fields_is_error(self):
        """Multiple fields is error."""
        result = self._tool().run({"formula": "C6H12O6", "name": "glucose"})
        self.assertEqual(result["status"], "error")
        self.assertIn("exactly one", result["error"])

    def test_network_exception_does_not_raise(self):
        """Network exception does not raise."""
        import requests

        with patch("tooluniverse.kegg_ext_tool.requests.get") as get:
            get.side_effect = requests.exceptions.ConnectionError("boom")
            result = self._tool().run({"name": "caffeine"})
        self.assertEqual(result["status"], "error")


# --------------------------------------------------------------------------- #
# metabolights_get_reference_compound
# --------------------------------------------------------------------------- #
class TestMetaboLightsReferenceCompound(unittest.TestCase):
    def _tool(self):
        from tooluniverse.metabolights_tool import MetaboLightsRESTTool

        return MetaboLightsRESTTool(
            {
                "name": "metabolights_get_reference_compound",
                "type": "MetaboLightsRESTTool",
                "fields": {
                    "endpoint": "https://www.ebi.ac.uk/metabolights/ws/compounds/{compound_id}",
                    "return_format": "JSON",
                },
            }
        )

    def test_single_compound_unwraps_content_dict(self):
        """Single compound unwraps content dict."""
        body = {
            "content": {
                "accession": "MTBLC10",
                "name": "(+)-Atherospermoline",
                "formula": "C36H38N2O6",
                "chebiId": "CHEBI:10",
                "inchikey": "XGEAUXVPBXUBKN-NSOVKSMOSA-N",
                "hasNMR": False,
                "hasMS": False,
            },
            "message": None,
            "err": None,
        }
        with patch("requests.Session.get") as get:
            get.return_value = _json_resp(200, body)
            result = self._tool().run({"compound_id": "MTBLC10"})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["accession"], "MTBLC10")
        self.assertEqual(result["data"]["formula"], "C36H38N2O6")
        self.assertEqual(result["count"], 1)
        self.assertTrue(get.call_args.args[0].endswith("/compounds/MTBLC10"))

    def test_list_returns_accession_array(self):
        """List returns accession array."""
        body = {"content": ["MTBLC10", "MTBLC100", "MTBLC10002"], "message": None}
        with patch("requests.Session.get") as get:
            get.return_value = _json_resp(200, body)
            result = self._tool().run({"list": True})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"], ["MTBLC10", "MTBLC100", "MTBLC10002"])
        self.assertEqual(result["count"], 3)
        self.assertTrue(get.call_args.args[0].endswith("/compounds/list"))

    def test_missing_args_is_error(self):
        """Missing args is error."""
        result = self._tool().run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("compound_id", result["error"])

    def test_http_error_does_not_raise(self):
        """Http error does not raise."""
        import requests

        err_resp = MagicMock()
        err_resp.status_code = 404
        http_err = requests.exceptions.HTTPError("404")
        http_err.response = err_resp
        with patch("requests.Session.get") as get:
            resp = _json_resp(404, {})
            resp.raise_for_status.side_effect = http_err
            get.return_value = resp
            result = self._tool().run({"compound_id": "MTBLC999999"})
        self.assertEqual(result["status"], "error")


# --------------------------------------------------------------------------- #
# LipidMaps_get_compound_by_xref
# --------------------------------------------------------------------------- #
class TestLipidMapsXref(unittest.TestCase):
    def _tool(self):
        from tooluniverse.lipidmaps_tool import LipidMapsTool

        return LipidMapsTool(
            {
                "name": "LipidMaps_get_compound_by_xref",
                "type": "LipidMapsTool",
                "fields": {"context": "compound", "input_item": "kegg_id"},
            }
        )

    def test_kegg_id_resolves_single_record(self):
        """Kegg id resolves single record."""
        import json as _json

        body = {
            "input": "C00157",
            "lm_id": "LMGP01010000",
            "name": "PC",
            "kegg_id": "C00157",
            "hmdb_id": "HMDB00564",
            "chebi_id": "57643",
        }
        with patch("tooluniverse.lipidmaps_tool.requests.get") as get:
            get.return_value = _json_resp(200, body, text=_json.dumps(body))
            result = self._tool().run(
                {"input_value": "C00157", "xref_type": "kegg_id"}
            )
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["lm_id"], "LMGP01010000")
        self.assertEqual(result["data"]["hmdb_id"], "HMDB00564")
        # xref_type drives the LMSD input item in the request path
        self.assertIn("/compound/kegg_id/C00157/all/json", get.call_args.args[0])

    def test_hmdb_id_overrides_config_default_input_item(self):
        """Hmdb id overrides config default input item."""
        import json as _json

        body = {"input": "HMDB0000564", "lm_id": "LMGP01010564", "name": "PC 16:0/16:0"}
        with patch("tooluniverse.lipidmaps_tool.requests.get") as get:
            get.return_value = _json_resp(200, body, text=_json.dumps(body))
            result = self._tool().run(
                {"input_value": "HMDB0000564", "xref_type": "hmdb_id"}
            )
        self.assertEqual(result["status"], "success")
        self.assertIn("/compound/hmdb_id/HMDB0000564/all/json", get.call_args.args[0])

    def test_unsupported_xref_type_is_error(self):
        """Unsupported xref type is error."""
        result = self._tool().run(
            {"input_value": "X", "xref_type": "not_a_real_xref"}
        )
        self.assertEqual(result["status"], "error")
        self.assertIn("Unsupported xref_type", result["error"])

    def test_missing_input_value_is_error(self):
        """Missing input value is error."""
        result = self._tool().run({"xref_type": "kegg_id"})
        self.assertEqual(result["status"], "error")
        self.assertIn("input_value", result["error"])

    def test_http_error_does_not_raise(self):
        """Http error does not raise."""
        import requests

        with patch("tooluniverse.lipidmaps_tool.requests.get") as get:
            get.side_effect = requests.exceptions.ConnectionError("down")
            result = self._tool().run(
                {"input_value": "C00157", "xref_type": "kegg_id"}
            )
        self.assertEqual(result["status"], "error")


# --------------------------------------------------------------------------- #
# SwissLipids_get_children
# --------------------------------------------------------------------------- #
class TestSwissLipidsChildren(unittest.TestCase):
    def _tool(self):
        from tooluniverse.swisslipids_tool import SwissLipidsTool

        return SwissLipidsTool(
            {
                "name": "SwissLipids_get_children",
                "type": "SwissLipidsTool",
                "fields": {"operation": "get_children"},
            }
        )

    def test_children_flattened_from_single_key_dicts(self):
        """Children flattened from single key dicts."""
        body = [
            {
                "SLM:000000338": {
                    "entity_id": "SLM:000000338",
                    "entity_name": "glycerone phosphate",
                    "entity_type": "metabolite",
                    "formula": "C3H5O6P",
                    "mass": "168.042000",
                    "inchikey": "GNGACRATGGDKBX-UHFFFAOYSA-L",
                }
            },
            {
                "SLM:000000340": {
                    "entity_id": "SLM:000000340",
                    "entity_name": "1,2-diacyl-sn-glycerol 3-diphosphate",
                    "entity_type": "metabolite",
                    "formula": "C5H5O11P2R2",
                }
            },
        ]
        with patch("tooluniverse.swisslipids_tool.requests.get") as get:
            get.return_value = _json_resp(200, body)
            result = self._tool().run({"entity_id": "SLM:000001193"})
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["data"]), 2)
        self.assertEqual(result["data"][0]["entity_id"], "SLM:000000338")
        self.assertEqual(result["data"][0]["entity_name"], "glycerone phosphate")
        self.assertEqual(result["metadata"]["child_count"], 2)
        self.assertEqual(get.call_args.kwargs["params"]["entity_id"], "SLM:000001193")

    def test_bare_number_gets_slm_prefix(self):
        """Bare number gets slm prefix."""
        with patch("tooluniverse.swisslipids_tool.requests.get") as get:
            get.return_value = _json_resp(200, [])
            self._tool().run({"entity_id": "000001193"})
        self.assertEqual(get.call_args.kwargs["params"]["entity_id"], "SLM:000001193")

    def test_missing_entity_id_is_error(self):
        """Missing entity id is error."""
        result = self._tool().run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("entity_id", result["error"])

    def test_http_500_becomes_friendly_not_found(self):
        """Http 500 becomes friendly not found."""
        tool = self._tool()
        with patch("tooluniverse.swisslipids_tool.requests.get") as get:
            r = MagicMock()
            r.status_code = 500
            r.text = "err"
            get.return_value = r
            result = tool.run({"entity_id": "SLM:999999999"})
        self.assertEqual(result["status"], "error")
        self.assertNotIn("HTTP 500", result["error"])
        self.assertIn("SwissLipids_search", result["error"])


if __name__ == "__main__":
    unittest.main()
