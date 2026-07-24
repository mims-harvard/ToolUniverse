"""Offline, mocked unit tests for Pep-Calc peptide-property tools.

Covers PepCalcTool (PepCalc_peptide_properties): a success-parse path that
merges the /peptide, /peptide/iso, and /peptide/extinction endpoints, and an
error path (Pep-Calc {message,status,errorCode} body). The HTTP layer
(request_with_retry) is mocked so the tests are deterministic and offline.
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

from tooluniverse.pepcalc_tool import PepCalcTool  # noqa: E402


# Real verified payloads from api.pep-calc.com for seq=ACDEFGHIK, C_term=NH2.
_PEPTIDE_AMIDE = {
    "seqString": "ACDEFGHIK",
    "seqList": ["A", "C", "D", "E", "F", "G", "H", "I", "K"],
    "nString": "H",
    "cString": "NH2",
    "nName": "Unmodified",
    "cName": "Amide",
    "nModified": False,
    "cModified": True,
    "seqLength": 9,
    "formula": "C44H67N13O13S",
    "molecularWeight": "1017.4702",
    "molecularWeightAverage": "1018.1580",
}
_ISO_AMIDE = {"pI": "6.96"}
_EXTINCTION = {"oxidized": 0, "reduced": 0}

# Real verified error payload for a malformed sequence.
_ERROR_BODY = {
    "message": "Peptide sequence input string incorrectly formatted.",
    "status": 400,
    "errorCode": "0003",
}


def _mock_response(json_value, status_code=200, raise_json=False):
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = "" if json_value is not None else "error"
    if raise_json:
        resp.json.side_effect = ValueError("no json")
    else:
        resp.json.return_value = json_value
    return resp


def _route(path_to_payload):
    """Return a request_with_retry side_effect that routes by URL path."""

    def _side_effect(_session, _method, url, **_kwargs):
        for path, payload in path_to_payload.items():
            if url.endswith(path):
                return _mock_response(payload)
        raise AssertionError(f"unexpected URL: {url}")

    return _side_effect


class TestPepCalcPeptideProperties(unittest.TestCase):
    def test_success_parse_merges_three_endpoints(self):
        """Merges /peptide, /peptide/iso, /peptide/extinction into one record."""
        tool = PepCalcTool({})
        routing = {
            "/peptide/iso": _ISO_AMIDE,
            "/peptide/extinction": _EXTINCTION,
            "/peptide": _PEPTIDE_AMIDE,
        }
        with patch(
            "tooluniverse.pepcalc_tool.request_with_retry"
        ) as req:
            req.side_effect = _route(routing)
            result = tool.run({"seq": "ACDEFGHIK", "C_term": "NH2"})

        self.assertEqual(result["status"], "success")
        data = result["data"]
        self.assertEqual(data["formula"], "C44H67N13O13S")
        self.assertEqual(data["molecularWeight"], "1017.4702")
        self.assertEqual(data["molecularWeightAverage"], "1018.1580")
        self.assertEqual(data["cName"], "Amide")
        self.assertTrue(data["cModified"])
        # pI is pulled from the /peptide/iso endpoint.
        self.assertEqual(data["isoelectricPoint"], "6.96")
        # extinction coefficient comes from /peptide/extinction.
        self.assertEqual(data["extinctionCoefficient"], {"oxidized": 0, "reduced": 0})
        self.assertEqual(result["metadata"]["C_term"], "NH2")

    def test_default_termini_forwarded(self):
        """When N_term/C_term omitted, 'H'/'OH' defaults are sent to the API."""
        tool = PepCalcTool({})
        captured = {}

        def _capture(_session, _method, url, **kwargs):
            if url.endswith("/peptide"):
                captured.update(kwargs.get("params") or {})
                return _mock_response(_PEPTIDE_AMIDE)
            return _mock_response(_ISO_AMIDE if url.endswith("/iso") else _EXTINCTION)

        with patch("tooluniverse.pepcalc_tool.request_with_retry") as req:
            req.side_effect = _capture
            tool.run({"seq": "ACDEFGHIK"})

        self.assertEqual(captured["N_term"], "H")
        self.assertEqual(captured["C_term"], "OH")
        self.assertEqual(captured["seq"], "ACDEFGHIK")

    def test_missing_seq_error(self):
        """Missing seq returns an error envelope without any HTTP call."""
        tool = PepCalcTool({})
        result = tool.run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("seq", result["error"])

    def test_api_error_body_maps_to_error(self):
        """A Pep-Calc {message,status,errorCode} body becomes an error envelope."""
        tool = PepCalcTool({})
        with patch("tooluniverse.pepcalc_tool.request_with_retry") as req:
            req.return_value = _mock_response(_ERROR_BODY, status_code=400)
            result = tool.run({"seq": "ACX123"})

        self.assertEqual(result["status"], "error")
        self.assertIn("incorrectly formatted", result["error"])
        self.assertEqual(result["errorCode"], "0003")

    def test_iso_failure_does_not_fail_whole_call(self):
        """If the iso endpoint errors, core properties still return with pI=None."""
        tool = PepCalcTool({})

        def _side_effect(_session, _method, url, **_kwargs):
            if url.endswith("/peptide/iso"):
                return _mock_response(_ERROR_BODY, status_code=400)
            if url.endswith("/peptide/extinction"):
                return _mock_response(_EXTINCTION)
            return _mock_response(_PEPTIDE_AMIDE)

        with patch("tooluniverse.pepcalc_tool.request_with_retry") as req:
            req.side_effect = _side_effect
            result = tool.run({"seq": "ACDEFGHIK", "C_term": "NH2"})

        self.assertEqual(result["status"], "success")
        self.assertIsNone(result["data"]["isoelectricPoint"])
        self.assertEqual(result["data"]["formula"], "C44H67N13O13S")

    def test_network_exception_returns_error(self):
        """A requests exception on the core call is caught and returned."""
        import requests

        tool = PepCalcTool({})
        with patch("tooluniverse.pepcalc_tool.request_with_retry") as req:
            req.side_effect = requests.exceptions.ConnectionError("boom")
            result = tool.run({"seq": "ACDEFGHIK"})

        self.assertEqual(result["status"], "error")
        self.assertIn("Request failed", result["error"])


if __name__ == "__main__":
    unittest.main()
