"""OpenGWAS two-sample MR instrument assembly + allele harmonization.

The tool chains /tophits (exposure instruments) and /associations (outcome
effects) and harmonizes both onto the exposure effect allele. These tests
mock the HTTP layer so the harmonization logic is verified without a token.
"""

import unittest
from unittest.mock import patch, MagicMock

import pytest

pytestmark = pytest.mark.unit


def _make_tool():
    from tooluniverse.opengwas_tool import OpenGWASTool

    return OpenGWASTool(
        {
            "name": "OpenGWAS_get_mr_instruments",
            "type": "OpenGWASTool",
            "fields": {"timeout": 60},
            "parameter": {"type": "object", "properties": {}, "required": []},
        }
    )


def _resp(payload):
    r = MagicMock()
    r.raise_for_status.return_value = None
    r.json.return_value = payload
    return r


class TestOpenGWASErrorPaths(unittest.TestCase):
    def test_missing_exposure_id(self):
        """Missing exposure_id is a clear error, not a crash."""
        result = _make_tool().run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("exposure_id is required", result["error"])

    def test_no_token(self):
        """Without OPENGWAS_JWT the tool explains how to get a token."""
        with patch.dict("os.environ", {"OPENGWAS_JWT": ""}, clear=False):
            result = _make_tool().run({"exposure_id": "ieu-a-2"})
        self.assertEqual(result["status"], "error")
        self.assertIn("api.opengwas.io", result["error"])


class TestOpenGWASHarmonization(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict("os.environ", {"OPENGWAS_JWT": "fake.jwt.token"})
        self.env.start()
        # Three exposure instruments: one allele-aligned, one allele-flipped,
        # one allele-incompatible; a fourth rsid is missing in the outcome.
        self.tophits = [
            {"rsid": "rs1", "ea": "A", "nea": "G", "eaf": 0.3, "beta": 0.10, "se": 0.01, "p": 1e-9},
            {"rsid": "rs2", "ea": "C", "nea": "T", "eaf": 0.4, "beta": 0.20, "se": 0.02, "p": 1e-10},
            {"rsid": "rs3", "ea": "A", "nea": "T", "eaf": 0.5, "beta": 0.05, "se": 0.01, "p": 1e-8},
            {"rsid": "rs4", "ea": "G", "nea": "A", "eaf": 0.2, "beta": 0.15, "se": 0.02, "p": 1e-9},
        ]
        self.assocs = [
            {"rsid": "rs1", "ea": "A", "nea": "G", "eaf": 0.3, "beta": 0.04, "se": 0.01, "p": 1e-4},
            # rs2 reported on the opposite allele -> beta sign should flip
            {"rsid": "rs2", "ea": "T", "nea": "C", "eaf": 0.6, "beta": -0.03, "se": 0.01, "p": 1e-3},
            # rs3 alleles incompatible (C/G vs A/T) -> dropped
            {"rsid": "rs3", "ea": "C", "nea": "G", "eaf": 0.5, "beta": 0.02, "se": 0.01, "p": 1e-2},
            # rs4 absent -> counted as missing
        ]

    def tearDown(self):
        self.env.stop()

    def test_harmonized_mr_input(self):
        tool = _make_tool()

        def fake_post(url, json=None, headers=None, timeout=None):
            return _resp(self.tophits if url.endswith("/tophits") else self.assocs)

        with patch("tooluniverse.opengwas_tool.requests.post", side_effect=fake_post):
            result = tool.run({"exposure_id": "ieu-a-2", "outcome_id": "ieu-a-7"})

        self.assertEqual(result["status"], "success")
        d = result["data"]
        self.assertEqual(d["n_instruments"], 4)
        # rs3 incompatible + rs4 missing -> 2 usable rows
        self.assertEqual(d["n_mr_input"], 2)
        self.assertEqual(result["metadata"]["n_missing_in_outcome"], 1)
        self.assertEqual(result["metadata"]["n_incompatible_alleles"], 1)

        rows = {r["rsid"]: r for r in d["mr_input"]}
        # rs1 aligned: outcome beta unchanged
        self.assertEqual(rows["rs1"]["harmonization"], "aligned")
        self.assertEqual(rows["rs1"]["outcome_beta"], 0.04)
        # rs2 flipped: outcome beta negated (-(-0.03) = 0.03)
        self.assertEqual(rows["rs2"]["harmonization"], "flipped")
        self.assertAlmostEqual(rows["rs2"]["outcome_beta"], 0.03)
        # exposure side preserved
        self.assertEqual(rows["rs2"]["exposure_beta"], 0.20)

    def test_no_instruments_carries_note(self):
        """Zero instruments returns success with an actionable note."""
        tool = _make_tool()
        with patch(
            "tooluniverse.opengwas_tool.requests.post",
            side_effect=lambda *a, **k: _resp([]),
        ):
            result = tool.run({"exposure_id": "ieu-a-2", "outcome_id": "ieu-a-7"})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["n_instruments"], 0)
        self.assertIn("note", result["metadata"])

    def test_exposure_only_when_no_outcome(self):
        """Omitting outcome_id returns instruments without an associations call."""
        tool = _make_tool()
        calls = []

        def fake_post(url, json=None, headers=None, timeout=None):
            calls.append(url)
            return _resp(self.tophits)

        with patch("tooluniverse.opengwas_tool.requests.post", side_effect=fake_post):
            result = tool.run({"exposure_id": "ieu-a-2"})

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["n_instruments"], 4)
        self.assertEqual(result["data"]["mr_input"], [])
        # Only /tophits should have been called, never /associations.
        self.assertTrue(all(u.endswith("/tophits") for u in calls))


if __name__ == "__main__":
    unittest.main()
