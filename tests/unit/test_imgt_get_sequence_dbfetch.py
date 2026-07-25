"""Regression tests for IMGT_get_sequence DBFetch handling (mocked HTTP).

The tool fetched sequences from EBI DBFetch with ``db=imgt`` -- not a valid
DBFetch database. DBFetch answers an unknown database with HTTP 200 and a body
of ``ERROR 1 Unknown database [imgt].``, so the old status-code-only check let
that error text through as the returned ``sequence`` under ``status: success``
(a valid input silently returning wrong data as success -- the documented
example M12950 was 100% broken). The fix queries the real ``imgtligm`` database,
detects DBFetch's HTTP-200 ``ERROR ...`` bodies, falls back to EMBL, and returns
a structured error when nothing resolves.
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


def _tool():
    from tooluniverse.imgt_tool import IMGTTool

    return IMGTTool({"name": "IMGT_get_sequence", "type": "IMGTTool"})


def _resp(text, status=200):
    r = MagicMock()
    r.status_code = status
    r.text = text
    r.raise_for_status.return_value = None
    return r


_REAL_FASTA = ">IMGTLIGM:M12950 M12950.1 Human TCR gamma V-region\ngagattctta\n"
_DBFETCH_ERR = "ERROR 1 Unknown database [imgt].\n"


class TestIMGTGetSequenceDBFetch(unittest.TestCase):
    def test_primary_query_uses_imgtligm_not_imgt(self):
        """The first DBFetch request must target the valid imgtligm database."""
        tool = _tool()
        with patch(
            "tooluniverse.imgt_tool.requests.get", return_value=_resp(_REAL_FASTA)
        ) as get:
            result = tool._get_sequence({"accession": "M12950", "format": "fasta"})
        self.assertEqual(get.call_args_list[0].kwargs["params"]["db"], "imgtligm")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["sequence"], _REAL_FASTA)

    def test_dbfetch_error_body_is_not_returned_as_sequence(self):
        """An HTTP-200 'ERROR ...' body must never surface as a success/sequence."""
        tool = _tool()
        # Both imgtligm and the embl fallback answer with DBFetch error bodies.
        with patch(
            "tooluniverse.imgt_tool.requests.get",
            side_effect=[_resp(_DBFETCH_ERR), _resp("ERROR 12 No entries found.\n")],
        ):
            result = tool._get_sequence({"accession": "BOGUS", "format": "fasta"})
        self.assertEqual(result["status"], "error")
        self.assertIn("BOGUS", result["error"])

    def test_falls_back_to_embl_when_imgtligm_misses(self):
        """imgtligm ERROR body triggers the EMBL fallback, which then succeeds."""
        tool = _tool()
        with patch(
            "tooluniverse.imgt_tool.requests.get",
            side_effect=[_resp(_DBFETCH_ERR), _resp(_REAL_FASTA)],
        ) as get:
            result = tool._get_sequence({"accession": "M12950", "format": "fasta"})
        self.assertEqual(get.call_args_list[1].kwargs["params"]["db"], "embl")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["sequence"], _REAL_FASTA)

    def test_missing_accession_errors_without_network(self):
        """No accession -> structured error and no HTTP call."""
        tool = _tool()
        with patch("tooluniverse.imgt_tool.requests.get") as get:
            result = tool._get_sequence({})
        self.assertEqual(result["status"], "error")
        get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
