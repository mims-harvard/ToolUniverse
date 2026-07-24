"""FAERS depth count tools: indication / drugcharacterization / reporter-qualification.

Covers three new FDADrugAdverseEventTool-backed count dimensions added to
fda_drug_adverse_event_tools.json:
  - FAERS_count_indications_by_drug   (count=patient.drug.drugindication.exact)
  - FAERS_count_drug_characterization (count=patient.drug.drugcharacterization)
  - FAERS_count_reporter_qualification(count=primarysource.qualification)

Each test mocks the openFDA HTTP call (no network) and checks both the parse /
code-decode path and the API-failure error path. The tool configs are loaded
from the shipped JSON so the tests exercise the real count_field + mapping.
"""

import json
import os
import unittest
from unittest.mock import MagicMock, patch

import pytest
import requests

pytestmark = pytest.mark.unit

_JSON_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "src",
    "tooluniverse",
    "data",
    "fda_drug_adverse_event_tools.json",
)


def _load_config(tool_name):
    with open(_JSON_PATH) as fh:
        configs = json.load(fh)
    for cfg in configs:
        if cfg.get("name") == tool_name:
            return cfg
    raise AssertionError(f"tool config not found: {tool_name}")


def _make_tool(tool_name):
    from tooluniverse.openfda_adv_tool import FDADrugAdverseEventTool

    return FDADrugAdverseEventTool(_load_config(tool_name))


def _patched_get(results):
    """Return a MagicMock patching requests.get to yield the given results list."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"results": results}
    resp.raise_for_status.return_value = None
    return resp


class TestIndicationsByDrug(unittest.TestCase):
    TOOL = "FAERS_count_indications_by_drug"

    def test_config_uses_drugindication_count_field(self):
        """Config wires count to patient.drug.drugindication.exact with a oneOf schema."""
        cfg = _load_config(self.TOOL)
        self.assertEqual(
            cfg["fields"]["return_fields"], ["patient.drug.drugindication.exact"]
        )
        # indication terms are free text, so no decode map is expected
        self.assertNotIn("return_fields_mapping", cfg["fields"])
        self.assertLessEqual(len(self.TOOL), 55)
        self.assertIn("oneOf", cfg["return_schema"])

    def test_parse_returns_term_count_rows(self):
        """Successful response yields ordered term/count indication rows."""
        tool = _make_tool(self.TOOL)
        rows = [
            {"term": "PRODUCT USED FOR UNKNOWN INDICATION", "count": 36767},
            {"term": "ATRIAL FIBRILLATION", "count": 15769},
        ]
        with patch(
            "tooluniverse.openfda_adv_tool.requests.get",
            return_value=_patched_get(rows),
        ) as get:
            out = tool.run({"medicinalproduct": "WARFARIN"})
            url = get.call_args.args[0]
        self.assertIn("count=patient.drug.drugindication.exact", url)
        self.assertIn("WARFARIN", url)
        self.assertEqual(out[0]["term"], "PRODUCT USED FOR UNKNOWN INDICATION")
        self.assertEqual(out[0]["count"], 36767)
        self.assertEqual(out[1]["term"], "ATRIAL FIBRILLATION")

    def test_api_failure_returns_error_not_raise(self):
        """A network failure surfaces an error entry and never raises."""
        tool = _make_tool(self.TOOL)
        with patch(
            "tooluniverse.openfda_adv_tool.requests.get",
            side_effect=requests.exceptions.ConnectionError("boom"),
        ):
            out = tool.run({"medicinalproduct": "WARFARIN"})
        # Tool must never raise; surfaces an error entry instead.
        self.assertIsInstance(out, list)
        self.assertIn("error", out[0])
        self.assertIn("API request failed", out[0]["error"])


class TestDrugCharacterization(unittest.TestCase):
    TOOL = "FAERS_count_drug_characterization"

    def test_config_decodes_role_codes(self):
        """Config maps drugcharacterization codes 1/2/3 to role labels."""
        cfg = _load_config(self.TOOL)
        mapping = cfg["fields"]["return_fields_mapping"][
            "patient.drug.drugcharacterization"
        ]
        self.assertEqual(mapping["1"], "Suspect")
        self.assertEqual(mapping["2"], "Concomitant")
        self.assertEqual(mapping["3"], "Interacting")
        self.assertLessEqual(len(self.TOOL), 55)
        self.assertIn("oneOf", cfg["return_schema"])

    def test_parse_decodes_integer_terms(self):
        """Integer code terms are decoded to human-readable labels."""
        tool = _make_tool(self.TOOL)
        # openFDA returns integer codes for this dimension
        rows = [
            {"term": 1, "count": 132943},
            {"term": 2, "count": 105667},
            {"term": 3, "count": 5371},
        ]
        with patch(
            "tooluniverse.openfda_adv_tool.requests.get",
            return_value=_patched_get(rows),
        ) as get:
            out = tool.run({"medicinalproduct": "WARFARIN"})
            url = get.call_args.args[0]
        self.assertIn("count=patient.drug.drugcharacterization", url)
        terms = {r["term"]: r["count"] for r in out}
        self.assertEqual(terms["Suspect"], 132943)
        self.assertEqual(terms["Concomitant"], 105667)
        self.assertEqual(terms["Interacting"], 5371)

    def test_unknown_code_passes_through(self):
        """An unmapped code is returned verbatim rather than dropped."""
        tool = _make_tool(self.TOOL)
        rows = [{"term": 4, "count": 15}]  # code 4 is not in the standard map
        with patch(
            "tooluniverse.openfda_adv_tool.requests.get",
            return_value=_patched_get(rows),
        ):
            out = tool.run({"medicinalproduct": "METFORMIN"})
        self.assertEqual(out[0]["term"], 4)
        self.assertEqual(out[0]["count"], 15)

    def test_api_failure_returns_error_not_raise(self):
        """A network failure surfaces an error entry and never raises."""
        tool = _make_tool(self.TOOL)
        with patch(
            "tooluniverse.openfda_adv_tool.requests.get",
            side_effect=requests.exceptions.Timeout("slow"),
        ):
            out = tool.run({"medicinalproduct": "WARFARIN"})
        self.assertIsInstance(out, list)
        self.assertIn("error", out[0])


class TestReporterQualification(unittest.TestCase):
    TOOL = "FAERS_count_reporter_qualification"

    def test_config_decodes_qualification_codes(self):
        """Config maps qualification codes 1-5 to reporter labels."""
        cfg = _load_config(self.TOOL)
        mapping = cfg["fields"]["return_fields_mapping"][
            "primarysource.qualification"
        ]
        self.assertEqual(mapping["1"], "Physician")
        self.assertEqual(mapping["2"], "Pharmacist")
        self.assertEqual(mapping["3"], "Other health professional")
        self.assertEqual(mapping["4"], "Lawyer")
        self.assertEqual(mapping["5"], "Consumer or non-health professional")
        self.assertLessEqual(len(self.TOOL), 55)
        self.assertIn("oneOf", cfg["return_schema"])

    def test_parse_decodes_integer_terms(self):
        """Integer code terms are decoded to human-readable labels."""
        tool = _make_tool(self.TOOL)
        rows = [
            {"term": 5, "count": 39363},
            {"term": 3, "count": 34629},
            {"term": 1, "count": 29597},
            {"term": 2, "count": 20653},
            {"term": 4, "count": 1106},
        ]
        with patch(
            "tooluniverse.openfda_adv_tool.requests.get",
            return_value=_patched_get(rows),
        ) as get:
            out = tool.run({"medicinalproduct": "WARFARIN"})
            url = get.call_args.args[0]
        self.assertIn("count=primarysource.qualification", url)
        terms = {r["term"]: r["count"] for r in out}
        self.assertEqual(terms["Consumer or non-health professional"], 39363)
        self.assertEqual(terms["Physician"], 29597)
        self.assertEqual(terms["Lawyer"], 1106)

    def test_api_failure_returns_error_not_raise(self):
        """A network failure surfaces an error entry and never raises."""
        tool = _make_tool(self.TOOL)
        with patch(
            "tooluniverse.openfda_adv_tool.requests.get",
            side_effect=requests.exceptions.ConnectionError("down"),
        ):
            out = tool.run({"medicinalproduct": "WARFARIN"})
        self.assertIsInstance(out, list)
        self.assertIn("error", out[0])


if __name__ == "__main__":
    unittest.main()
