"""Offline, mocked unit tests for the PeptideAtlas observed-peptide tool.

Covers PeptideAtlasGetObservedPeptidesTool (PeptideAtlas_get_observed_peptides):
success-parse paths (protein-constrained and build-level) plus error paths
(empty result, HTTP error, non-JSON body, network exception). The HTTP layer
(requests.get) is mocked so the tests are deterministic and run without
network access.
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

from tooluniverse.peptideatlas_tool import (  # noqa: E402
    PeptideAtlasGetObservedPeptidesTool,
)


_PEPTIDE_P02768 = [
    {
        "SSRCalc_relative_hydrophobicity": "28.82",
        "protease_ids": "1,7,10",
        "n_genome_locations": 1,
        "peptide_accession": "PAp00000092",
        "is_subpeptide_of": "4383858,7889874",
        "n_samples": 57,
        "best_probability": "1.000",
        "n_protein_mappings": 10,
        "is_exon_spanning": "Y",
        "peptide_sequence": "SLHTLFGDKLCT",
        "organism_full_name": "Homo sapiens",
        "atlas build name": "Human 2024-01",
        "n_observations": 367,
        "empirical_proteotypic_score": "0.03",
    }
]

_BUILD_LEVEL = [
    {
        "peptide_accession": "PAp00000001",
        "peptide_sequence": "AAHEEICTTNEGVMYR",
        "n_observations": 15447,
        "n_samples": 402,
        "best_probability": "1.000",
        "n_protein_mappings": 43,
        "n_genome_locations": 1,
        "is_exon_spanning": "Y",
        "empirical_proteotypic_score": "0.28",
        "SSRCalc_relative_hydrophobicity": "23.01",
        "protease_ids": "6,,1,9,10",
        "is_subpeptide_of": "12602,2329447",
        "organism_full_name": "Homo sapiens",
        "atlas build name": "Human 2024-01",
    },
    {
        "peptide_accession": "PAp00000003",
        "peptide_sequence": "ALCELESGIPAAESQIVYAERPLTDNHR",
        "n_observations": 2726,
        "n_samples": 351,
        "best_probability": "1.000",
        "n_protein_mappings": 6,
        "n_genome_locations": 1,
        "is_exon_spanning": "Y",
        "empirical_proteotypic_score": "0.67",
        "SSRCalc_relative_hydrophobicity": "37.95",
        "protease_ids": "6,,1,10",
        "is_subpeptide_of": "8428930",
        "organism_full_name": "Homo sapiens",
        "atlas build name": "Human 2024-01",
    },
]


def _mock_response(
    json_value=None,
    status_code=200,
    raise_json=False,
    url="https://db.systemsbiology.net/sbeams/cgi/PeptideAtlas/GetPeptides",
):
    resp = MagicMock()
    resp.status_code = status_code
    resp.url = url
    resp.text = "" if json_value is not None else "<html>error</html>"
    if raise_json:
        resp.json.side_effect = ValueError("no json")
    else:
        resp.json.return_value = json_value
    return resp


class TestPeptideAtlasGetObservedPeptides(unittest.TestCase):
    def test_success_protein_constrained(self):
        """Parses a protein-constrained array and forwards exact CGI params."""
        tool = PeptideAtlasGetObservedPeptidesTool({})
        with patch("tooluniverse.peptideatlas_tool.requests.get") as get:
            get.return_value = _mock_response(_PEPTIDE_P02768)
            result = tool.run({"biosequence_name": "P02768", "row_limit": 5})

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["metadata"]["returned_count"], 1)
        self.assertEqual(result["metadata"]["biosequence_name"], "P02768")
        self.assertEqual(result["metadata"]["atlas_build_id"], 572)
        self.assertEqual(result["metadata"]["row_limit"], 5)
        first = result["data"][0]
        self.assertEqual(first["peptide_accession"], "PAp00000092")
        self.assertEqual(first["peptide_sequence"], "SLHTLFGDKLCT")
        self.assertEqual(first["n_observations"], 367)
        self.assertEqual(first["n_samples"], 57)

        # The PeptideAtlas-exact CGI params must be forwarded.
        sent = get.call_args.kwargs["params"]
        self.assertEqual(sent["biosequence_name_constraint"], "P02768")
        self.assertEqual(sent["atlas_build_id"], 572)
        self.assertEqual(sent["output_mode"], "json")
        self.assertEqual(sent["apply_action"], "QUERY")
        self.assertEqual(sent["row_limit"], 5)

    def test_success_build_level_no_constraint(self):
        """Build-level query omits biosequence_name_constraint."""
        tool = PeptideAtlasGetObservedPeptidesTool({})
        with patch("tooluniverse.peptideatlas_tool.requests.get") as get:
            get.return_value = _mock_response(_BUILD_LEVEL)
            result = tool.run({"row_limit": 2})

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["metadata"]["returned_count"], 2)
        self.assertIsNone(result["metadata"]["biosequence_name"])
        self.assertEqual(result["data"][0]["peptide_accession"], "PAp00000001")
        self.assertEqual(result["data"][0]["n_observations"], 15447)

        sent = get.call_args.kwargs["params"]
        self.assertNotIn("biosequence_name_constraint", sent)
        self.assertEqual(sent["row_limit"], 2)

    def test_string_args_coerced(self):
        """String atlas_build_id / row_limit are coerced to ints."""
        tool = PeptideAtlasGetObservedPeptidesTool({})
        with patch("tooluniverse.peptideatlas_tool.requests.get") as get:
            get.return_value = _mock_response(_BUILD_LEVEL)
            tool.run({"atlas_build_id": "572", "row_limit": "2"})
        sent = get.call_args.kwargs["params"]
        self.assertEqual(sent["atlas_build_id"], 572)
        self.assertEqual(sent["row_limit"], 2)

    def test_empty_result_error(self):
        """An empty array yields a no-peptides error envelope."""
        tool = PeptideAtlasGetObservedPeptidesTool({})
        with patch("tooluniverse.peptideatlas_tool.requests.get") as get:
            get.return_value = _mock_response([])
            result = tool.run({"biosequence_name": "NOSUCHPROT"})
        self.assertEqual(result["status"], "error")
        self.assertIn("No observed peptides", result["error"])

    def test_http_error(self):
        """A non-200 HTTP status maps to an error envelope."""
        tool = PeptideAtlasGetObservedPeptidesTool({})
        with patch("tooluniverse.peptideatlas_tool.requests.get") as get:
            get.return_value = _mock_response(None, status_code=500)
            result = tool.run({"biosequence_name": "P02768"})
        self.assertEqual(result["status"], "error")
        self.assertIn("HTTP 500", result["error"])

    def test_non_json_response_error(self):
        """A non-JSON body returns an error envelope."""
        tool = PeptideAtlasGetObservedPeptidesTool({})
        with patch("tooluniverse.peptideatlas_tool.requests.get") as get:
            get.return_value = _mock_response(None, raise_json=True)
            result = tool.run({"biosequence_name": "P02768"})
        self.assertEqual(result["status"], "error")
        self.assertIn("non-JSON", result["error"])

    def test_network_exception_returns_error(self):
        """A requests exception is caught and returned as an error."""
        import requests

        tool = PeptideAtlasGetObservedPeptidesTool({})
        with patch("tooluniverse.peptideatlas_tool.requests.get") as get:
            get.side_effect = requests.exceptions.Timeout("slow")
            result = tool.run({"biosequence_name": "P02768"})
        self.assertEqual(result["status"], "error")
        self.assertIn("failed", result["error"])


if __name__ == "__main__":
    unittest.main()
