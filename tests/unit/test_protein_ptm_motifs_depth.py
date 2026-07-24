"""Protein PTM / motif depth tools: parse + error-path coverage (mocked HTTP).

Covers two new tools that close confirmed capability gaps in the
``protein-ptm-motifs`` cluster:

* ``iPTMnet_get_proteoform_ppi`` (iPTMnetTool, operation ``get_proteoform_ppi``)
  — proteoform-state-level protein-protein interactions keyed on PRO ontology
  proteoform IDs (isoform + modification state), from the iPTMnet
  ``/{ac}/proteoformsppi`` endpoint. Distinct from the residue-level
  ``/ptmppi`` data already exposed by ``iPTMnet_get_ptm_ppi``.

* ``ScanProsite_find_proteins_with_motif`` (PROSITETool, endpoint
  ``find_proteins_with_motif``) — reverse motif scan: given a PROSITE signature
  accession, enumerate all UniProtKB/Swiss-Prot proteins containing that motif,
  with per-match positions. Inverse of the forward protein->motifs scan.

All network calls are mocked; these tests never touch the live APIs.
"""

import unittest
from unittest.mock import patch, MagicMock

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# iPTMnet_get_proteoform_ppi
# ---------------------------------------------------------------------------


def _iptmnet_tool():
    from tooluniverse.iptmnet_tool import iPTMnetTool

    return iPTMnetTool(
        {
            "name": "iPTMnet_get_proteoform_ppi",
            "parameter": {"required": ["operation", "uniprot_id"]},
        }
    )


# Real-shaped payload from GET /api/Q15796/proteoformsppi (SMAD2).
_IPTMNET_PROTEOFORM_PPI = [
    {
        "protein_1": {"pro_id": "PR:000025934", "label": "hSMAD2/iso:Long/Phos:1"},
        "relation": "Interaction",
        "protein_2": {"pro_id": "PR:Q13485", "label": "hSMAD4"},
        "source": {"name": "PRO", "label": "pro"},
        "pmids": ["9311995"],
    },
    {
        "protein_1": {"pro_id": "PR:000045371", "label": "hSMAD2/iso:Long/UnPhos:1"},
        "relation": "Interaction",
        "protein_2": {},
        "source": {"name": "PRO"},
        "pmids": ["8980228"],
    },
]


class TestIPTMnetProteoformPPI(unittest.TestCase):
    def test_parses_proteoform_keyed_interactions(self):
        """PRO ontology proteoform IDs + labels are surfaced for both interactants."""
        tool = _iptmnet_tool()
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = _IPTMNET_PROTEOFORM_PPI
        with patch.object(tool.session, "get", return_value=resp) as get:
            result = tool.run(
                {"operation": "get_proteoform_ppi", "uniprot_id": "Q15796"}
            )

        # Hit the proteoformsppi endpoint, not ptmppi.
        called_url = get.call_args[0][0]
        self.assertTrue(called_url.endswith("/Q15796/proteoformsppi"))

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["metadata"]["total_interactions"], 2)

        first = result["data"][0]
        self.assertEqual(first["protein_1_pro_id"], "PR:000025934")
        self.assertEqual(first["protein_1_label"], "hSMAD2/iso:Long/Phos:1")
        self.assertEqual(first["relation"], "Interaction")
        self.assertEqual(first["protein_2_pro_id"], "PR:Q13485")
        self.assertEqual(first["protein_2_label"], "hSMAD4")
        self.assertEqual(first["source"], "PRO")
        self.assertEqual(first["pmids"], ["9311995"])

        # Missing protein_2 must not raise; empty strings instead.
        second = result["data"][1]
        self.assertEqual(second["protein_2_pro_id"], "")
        self.assertEqual(second["protein_2_label"], "")

    def test_operation_inferred_from_tool_name(self):
        """Tool name alone selects get_proteoform_ppi (not get_proteoforms)."""
        tool = _iptmnet_tool()
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = _IPTMNET_PROTEOFORM_PPI
        with patch.object(tool.session, "get", return_value=resp) as get:
            result = tool.run({"uniprot_id": "Q15796"})
        self.assertEqual(result["status"], "success")
        self.assertTrue(get.call_args[0][0].endswith("/Q15796/proteoformsppi"))

    def test_missing_uniprot_id_errors(self):
        """No uniprot_id -> structured error, no network call, no raise."""
        tool = _iptmnet_tool()
        with patch.object(tool.session, "get") as get:
            result = tool.run({"operation": "get_proteoform_ppi"})
        self.assertEqual(result["status"], "error")
        self.assertIn("uniprot_id", result["error"])
        get.assert_not_called()

    def test_not_found_returns_error(self):
        """404 from iPTMnet -> structured error envelope, never raises."""
        tool = _iptmnet_tool()
        resp = MagicMock()
        resp.status_code = 404
        with patch.object(tool.session, "get", return_value=resp):
            result = tool.run(
                {"operation": "get_proteoform_ppi", "uniprot_id": "NOPE99"}
            )
        self.assertEqual(result["status"], "error")
        self.assertIn("NOPE99", result["error"])

    def test_network_error_is_caught(self):
        """A raised requests exception is swallowed into an error envelope."""
        import requests

        tool = _iptmnet_tool()
        with patch.object(
            tool.session, "get", side_effect=requests.exceptions.ConnectionError()
        ):
            result = tool.run(
                {"operation": "get_proteoform_ppi", "uniprot_id": "Q15796"}
            )
        self.assertEqual(result["status"], "error")


# ---------------------------------------------------------------------------
# ScanProsite_find_proteins_with_motif
# ---------------------------------------------------------------------------


def _prosite_reverse_tool():
    from tooluniverse.prosite_tool import PROSITETool

    return PROSITETool(
        {
            "name": "ScanProsite_find_proteins_with_motif",
            "fields": {"endpoint": "find_proteins_with_motif"},
        }
    )


# Real-shaped payload from POST sig=PS00029&db=sprot&output=json (LEUCINE_ZIPPER).
_SCANPROSITE_REVERSE = {
    "n_match": 13839,
    "n_seq": 10000,
    "capped": 1,
    "matchset": [
        {
            "sequence_ac": "Q6GZW6",
            "sequence_id": "009L_FRG3G",
            "sequence_db": "sp",
            "start": 99,
            "stop": 120,
            "signature_ac": "PS00029",
            "signature_id": "LEUCINE_ZIPPER",
        },
        {
            "sequence_ac": "Q91G56",
            "sequence_id": "042R_IIV6",
            "sequence_db": "sp",
            "start": 14,
            "stop": 35,
            "signature_ac": "PS00029",
            "signature_id": "LEUCINE_ZIPPER",
        },
    ],
}


class TestScanPrositeFindProteinsWithMotif(unittest.TestCase):
    def test_parses_reverse_motif_matches(self):
        """Signature -> proteins parsing surfaces accession, name, positions."""
        tool = _prosite_reverse_tool()
        resp = MagicMock()
        resp.text = "{...}"
        resp.json.return_value = _SCANPROSITE_REVERSE
        resp.raise_for_status.return_value = None
        with patch("tooluniverse.prosite_tool.requests.post", return_value=resp) as post:
            result = tool.run({"signature_ac": "PS00029", "max_results": 5})

        # POST body carries the signature + Swiss-Prot db + json output.
        sent = post.call_args.kwargs["data"]
        self.assertEqual(sent["sig"], "PS00029")
        self.assertEqual(sent["db"], "sprot")
        self.assertEqual(sent["output"], "json")
        self.assertEqual(sent["skip"], "yes")

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["metadata"]["total_matches"], 13839)
        self.assertEqual(result["metadata"]["total_sequences"], 10000)
        self.assertTrue(result["metadata"]["capped"])
        self.assertEqual(result["metadata"]["returned"], 2)

        first = result["data"][0]
        self.assertEqual(first["sequence_ac"], "Q6GZW6")
        self.assertEqual(first["sequence_id"], "009L_FRG3G")
        self.assertEqual(first["start"], 99)
        self.assertEqual(first["stop"], 120)
        self.assertEqual(first["signature_ac"], "PS00029")
        self.assertEqual(first["signature_id"], "LEUCINE_ZIPPER")

    def test_max_results_caps_returned_records(self):
        """max_results limits returned rows but not the reported total_matches."""
        tool = _prosite_reverse_tool()
        resp = MagicMock()
        resp.text = "{...}"
        resp.json.return_value = _SCANPROSITE_REVERSE
        resp.raise_for_status.return_value = None
        with patch("tooluniverse.prosite_tool.requests.post", return_value=resp):
            result = tool.run({"signature_ac": "PS00029", "max_results": 1})
        self.assertEqual(len(result["data"]), 1)
        self.assertEqual(result["metadata"]["total_matches"], 13839)

    def test_skip_frequent_false_sends_skip_no(self):
        """skip_frequent=False overrides SKIP-FLAG signatures (skip=no)."""
        tool = _prosite_reverse_tool()
        resp = MagicMock()
        resp.text = "{...}"
        resp.json.return_value = {"n_match": 0, "n_seq": 0, "matchset": []}
        resp.raise_for_status.return_value = None
        with patch("tooluniverse.prosite_tool.requests.post", return_value=resp) as post:
            tool.run({"signature_ac": "PS00005", "skip_frequent": False})
        self.assertEqual(post.call_args.kwargs["data"]["skip"], "no")

    def test_missing_signature_errors(self):
        """No signature accession -> structured error, no network call."""
        tool = _prosite_reverse_tool()
        with patch("tooluniverse.prosite_tool.requests.post") as post:
            result = tool.run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("signature_ac", result["error"])
        post.assert_not_called()

    def test_invalid_signature_prefix_errors(self):
        """A signature not starting with PS is rejected before any network call."""
        tool = _prosite_reverse_tool()
        with patch("tooluniverse.prosite_tool.requests.post") as post:
            result = tool.run({"signature_ac": "ZZ123"})
        self.assertEqual(result["status"], "error")
        self.assertIn("PS", result["error"])
        post.assert_not_called()

    def test_html_error_page_returns_error(self):
        """An HTML page (invalid signature) -> structured error, not a parse crash."""
        tool = _prosite_reverse_tool()
        resp = MagicMock()
        resp.text = "<!DOCTYPE HTML><html><body>bad</body></html>"
        resp.raise_for_status.return_value = None
        with patch("tooluniverse.prosite_tool.requests.post", return_value=resp):
            result = tool.run({"signature_ac": "PS99999"})
        self.assertEqual(result["status"], "error")

    def test_chunked_encoding_error_is_caught(self):
        """Truncated responses for frequent signatures -> clean error, no raise."""
        import requests

        tool = _prosite_reverse_tool()
        with patch(
            "tooluniverse.prosite_tool.requests.post",
            side_effect=requests.exceptions.ChunkedEncodingError(),
        ):
            result = tool.run({"signature_ac": "PS00005", "skip_frequent": False})
        self.assertEqual(result["status"], "error")
        self.assertIn("SKIP-FLAG", result["error"])


if __name__ == "__main__":
    unittest.main()
