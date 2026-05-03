"""
Tests for Round 72 bug fixes in proteomics/structural biology tools.

Covers:
- Feature-72A-001: alphafold_get_annotations invalid test_example "F1"
- Feature-72A-003: BLAST wrong BioPython attribute names (hit_length, hit_start, hit_end)
- Feature-72A-004: MobiDB dead base URL (mobidb.bio.unipd.it -> mobidb.org)
- Feature-72A-005: EVE protein_change always None (hgvsp -> amino_acids)
- Feature-72A-006: pdbe_get_entry_quality broken endpoint
- Feature-72A-007: PROSITE signature_name always None (signature_id -> removed)
- Feature-72A-010: DisProt wrong base URL (missing www.)
"""

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

SRC_ROOT = Path(__file__).parent.parent.parent / "src"
DATA_DIR = SRC_ROOT / "tooluniverse" / "data"


# Some tool modules import from .tool_registry which is dynamically registered.
# Provide a stub so direct imports work in the test environment.
def _ensure_registry_stub():
    """Install a stub for tooluniverse.tool_registry if not already present."""
    if "tooluniverse.tool_registry" not in sys.modules:
        stub = MagicMock()
        stub.register_tool = lambda name: (lambda cls: cls)
        sys.modules["tooluniverse.tool_registry"] = stub


_ensure_registry_stub()


# ---------------------------------------------------------------------------
# Feature-72A-001: alphafold_get_annotations invalid test_example
# ---------------------------------------------------------------------------
class TestAlphafoldAnnotationsTestExample(unittest.TestCase):
    """Feature-72A-001: alphafold_get_annotations had 'F1' as test_example (invalid accession)."""

    def test_annotations_test_example_is_valid_uniprot_accession(self):
        """test_examples must use a valid UniProt accession, not 'F1'."""
        with open(DATA_DIR / "alphafold_tools.json") as f:
            tools = json.load(f)
        annotations_tool = next(t for t in tools if t["name"] == "alphafold_get_annotations")
        examples = annotations_tool.get("test_examples", [])
        self.assertTrue(len(examples) > 0, "alphafold_get_annotations must have at least one test_example")
        qualifier = examples[0].get("qualifier", "")
        # Valid UniProt accessions are 6-10 chars like P04637, Q5SWX9
        self.assertNotEqual(qualifier, "F1", "test_example must not be 'F1' (invalid accession)")
        self.assertGreaterEqual(len(qualifier), 6, f"qualifier '{qualifier}' looks too short for a UniProt accession")

    def test_get_prediction_test_example_unchanged(self):
        """alphafold_get_prediction should keep its valid test_example P69905."""
        with open(DATA_DIR / "alphafold_tools.json") as f:
            tools = json.load(f)
        pred_tool = next(t for t in tools if t["name"] == "alphafold_get_prediction")
        examples = pred_tool.get("test_examples", [])
        self.assertEqual(examples[0]["qualifier"], "P69905")


# ---------------------------------------------------------------------------
# Feature-72A-003: BLAST wrong BioPython attribute names
# ---------------------------------------------------------------------------
class TestBlastBioPythonAttributes(unittest.TestCase):
    """Feature-72A-003: BLAST _parse_blast_results used wrong attribute names."""

    def test_blast_uses_alignment_length_not_hit_length(self):
        """hit_length should use alignment.length (BioPython), not alignment.hit_length."""
        with open(SRC_ROOT / "tooluniverse" / "blast_tool.py") as f:
            content = f.read()
        # Must use alignment.length
        self.assertIn('"hit_length": getattr(alignment, "length"', content,
                      "hit_length must use alignment.length (BioPython attribute)")
        # Must NOT use the old wrong attribute
        self.assertNotIn('"hit_length": getattr(alignment, "hit_length"', content,
                         "hit_length must not use alignment.hit_length (does not exist in BioPython)")

    def test_blast_uses_sbjct_start_not_hit_start(self):
        """hit_start should use hsp.sbjct_start (BioPython), not hsp.hit_start."""
        with open(SRC_ROOT / "tooluniverse" / "blast_tool.py") as f:
            content = f.read()
        self.assertIn('"hit_start": getattr(hsp, "sbjct_start"', content,
                      "hit_start must use hsp.sbjct_start (BioPython attribute)")
        self.assertNotIn('"hit_start": getattr(hsp, "hit_start"', content,
                         "hit_start must not use hsp.hit_start (does not exist in BioPython)")

    def test_blast_uses_sbjct_end_not_hit_end(self):
        """hit_end should use hsp.sbjct_end (BioPython), not hsp.hit_end."""
        with open(SRC_ROOT / "tooluniverse" / "blast_tool.py") as f:
            content = f.read()
        self.assertIn('"hit_end": getattr(hsp, "sbjct_end"', content,
                      "hit_end must use hsp.sbjct_end (BioPython attribute)")
        self.assertNotIn('"hit_end": getattr(hsp, "hit_end"', content,
                         "hit_end must not use hsp.hit_end (does not exist in BioPython)")

    def test_blast_parse_results_with_mock_alignment(self):
        """_parse_blast_results should correctly extract hit_length using .length."""
        from tooluniverse.blast_tool import NCBIBlastTool

        config = {
            "name": "BLAST_protein_search",
            "type": "NCBIBlastTool",
            "parameter": {"type": "object", "properties": {}, "required": []},
            "fields": {},
        }
        tool = NCBIBlastTool(config)

        # Create mock alignment with correct BioPython attribute names
        mock_alignment = MagicMock()
        mock_alignment.hit_id = "sp|P04637|P53_HUMAN"
        mock_alignment.hit_def = "Cellular tumor antigen p53"
        mock_alignment.length = 393  # BioPython uses .length

        mock_hsp = MagicMock()
        mock_hsp.score = 2000.0
        mock_hsp.bits = 776.0
        mock_hsp.expect = 0.0
        mock_hsp.identities = 390
        mock_hsp.positives = 390
        mock_hsp.gaps = 0
        mock_hsp.align_length = 393
        mock_hsp.query_start = 1
        mock_hsp.query_end = 393
        mock_hsp.sbjct_start = 1   # BioPython uses sbjct_start
        mock_hsp.sbjct_end = 393   # BioPython uses sbjct_end
        mock_hsp.query = "MEEPQSDPS"
        mock_hsp.match = "MEEPQSDPS"
        mock_hsp.sbjct = "MEEPQSDPS"

        mock_alignment.hsps = [mock_hsp]

        mock_record = MagicMock()
        mock_record.query_id = "test_query"
        mock_record.query_length = 393
        mock_record.database = "nr"
        mock_record.application = "BLASTP"
        mock_record.alignments = [mock_alignment]

        with patch("tooluniverse.blast_tool.NCBIXML") as mock_xml:
            mock_xml.read.return_value = mock_record
            result = tool._parse_blast_results("<fake_xml/>")

        self.assertNotIn("error", result)
        self.assertEqual(len(result["alignments"]), 1)
        aln = result["alignments"][0]
        # hit_length should be 393 (from .length), not 0 (from nonexistent .hit_length)
        self.assertEqual(aln["hit_length"], 393,
                         "hit_length must be 393 (from alignment.length), not 0")
        hsp = aln["hsps"][0]
        self.assertEqual(hsp["hit_start"], 1,
                         "hit_start must be 1 (from hsp.sbjct_start), not 0")
        self.assertEqual(hsp["hit_end"], 393,
                         "hit_end must be 393 (from hsp.sbjct_end), not 0")


# ---------------------------------------------------------------------------
# Feature-72A-004: MobiDB dead base URL
# ---------------------------------------------------------------------------
class TestMobiDBBaseURL(unittest.TestCase):
    """Feature-72A-004: MobiDB used dead URL mobidb.bio.unipd.it instead of mobidb.org."""

    def test_mobidb_base_url_is_correct(self):
        """MOBIDB_BASE_URL must point to mobidb.org, not the dead mobidb.bio.unipd.it."""
        with open(SRC_ROOT / "tooluniverse" / "mobidb_tool.py") as f:
            content = f.read()
        self.assertIn("mobidb.org", content, "mobidb_tool.py must reference mobidb.org")
        self.assertNotIn("mobidb.bio.unipd.it", content,
                         "mobidb_tool.py must not reference dead URL mobidb.bio.unipd.it")

    def test_mobidb_constant_value(self):
        """MOBIDB_BASE_URL constant must be set to https://mobidb.org/api/download."""
        import importlib
        import tooluniverse.mobidb_tool as m
        importlib.reload(m)
        self.assertEqual(m.MOBIDB_BASE_URL, "https://mobidb.org/api/download")

    def test_mobidb_error_message_updated(self):
        """Connection error message must reference mobidb.org, not the old dead domain."""
        with open(SRC_ROOT / "tooluniverse" / "mobidb_tool.py") as f:
            content = f.read()
        # Error message should not reference the old dead URL
        self.assertNotIn("mobidb.bio.unipd.it", content)


# ---------------------------------------------------------------------------
# Feature-72A-005: EVE protein_change always None (hgvsp does not exist in VEP)
# ---------------------------------------------------------------------------
class TestEVEProteinChange(unittest.TestCase):
    """Feature-72A-005: EVE used tc.get('hgvsp') which VEP never returns."""

    def test_eve_no_longer_uses_hgvsp(self):
        """eve_tool.py must not reference 'hgvsp' field (not in VEP response)."""
        with open(SRC_ROOT / "tooluniverse" / "eve_tool.py") as f:
            content = f.read()
        self.assertNotIn("hgvsp", content,
                         "EVE tool must not use 'hgvsp' - it does not exist in VEP API response")

    def test_eve_uses_amino_acids_field(self):
        """EVE must use VEP's 'amino_acids' field to construct protein_change."""
        with open(SRC_ROOT / "tooluniverse" / "eve_tool.py") as f:
            content = f.read()
        self.assertIn("amino_acids", content,
                      "EVE tool must use 'amino_acids' field from VEP response")
        self.assertIn("protein_start", content,
                      "EVE tool must use 'protein_start' field from VEP response")

    def test_eve_includes_eve_class_from_vep(self):
        """EVE result must include 'eve_class' from VEP response (not just local threshold)."""
        with open(SRC_ROOT / "tooluniverse" / "eve_tool.py") as f:
            content = f.read()
        self.assertIn('"eve_class": tc.get("eve_class")', content,
                      "EVE tool must propagate VEP's eve_class field directly")

    def test_eve_protein_change_construction(self):
        """EVE _get_variant_score must build protein_change from amino_acids+protein_start."""
        from tooluniverse.eve_tool import EVETool

        config = {
            "name": "EVE_get_variant_score",
            "type": "EVETool",
            "parameter": {"type": "object", "properties": {}, "required": []},
            "fields": {"operation": "get_variant_score"},
        }
        tool = EVETool(config)

        # Mock VEP response with amino_acids (VEP format) instead of hgvsp
        mock_vep_response = [
            {
                "input": "9:5030551-5030551:1/A",
                "transcript_consequences": [
                    {
                        "transcript_id": "ENST00000269305",
                        "gene_symbol": "TP53",
                        "amino_acids": "R/L",       # VEP field (not hgvsp)
                        "protein_start": 248,        # VEP field
                        "eve_score": 0.82,
                        "eve_class": "Pathogenic",   # VEP field
                        "consequence_terms": ["missense_variant"],
                        "sift_prediction": "deleterious",
                        "polyphen_prediction": "probably_damaging",
                    }
                ],
            }
        ]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_vep_response

        with patch("requests.get", return_value=mock_response):
            result = tool.run({"variant": "ENST00000269305.4:c.743G>T"})

        self.assertEqual(result["status"], "success")
        scores = result["data"]["eve_scores"]
        self.assertEqual(len(scores), 1)
        # protein_change must be constructed as "p.R248L" not None
        self.assertEqual(scores[0]["protein_change"], "p.R248L",
                         "protein_change must be 'p.R248L' constructed from amino_acids+protein_start")
        # eve_class must be passed through from VEP
        self.assertEqual(scores[0]["eve_class"], "Pathogenic",
                         "eve_class must be propagated from VEP response")


# ---------------------------------------------------------------------------
# Feature-72A-006: pdbe_get_entry_quality broken endpoint
# ---------------------------------------------------------------------------
class TestPDBeQualityEndpoint(unittest.TestCase):
    """Feature-72A-006: pdbe_get_entry_quality used /pdb/entry/quality/ which always returns 404."""

    def test_pdbe_quality_endpoint_in_json_is_correct(self):
        """JSON config must use the validation/summary_quality_scores/entry endpoint."""
        with open(DATA_DIR / "pdbe_api_tools.json") as f:
            tools = json.load(f)
        quality_tool = next(t for t in tools if t["name"] == "pdbe_get_entry_quality")
        endpoint = quality_tool["fields"]["endpoint"]
        self.assertIn("validation/summary_quality_scores/entry", endpoint,
                      f"Endpoint '{endpoint}' must use validation/summary_quality_scores/entry path")
        self.assertNotIn("/pdb/entry/quality/", endpoint,
                         "Old /pdb/entry/quality/ endpoint always returns 404 and must be removed")

    def test_pdbe_quality_has_test_examples(self):
        """pdbe_get_entry_quality must have non-empty test_examples."""
        with open(DATA_DIR / "pdbe_api_tools.json") as f:
            tools = json.load(f)
        quality_tool = next(t for t in tools if t["name"] == "pdbe_get_entry_quality")
        examples = quality_tool.get("test_examples", [])
        self.assertGreater(len(examples), 0,
                           "pdbe_get_entry_quality must have at least one test_example")

    def test_pdbe_api_tool_fallback_uses_correct_url(self):
        """pdbe_api_tool.py fallback URL for quality must use validation endpoint."""
        with open(SRC_ROOT / "tooluniverse" / "pdbe_api_tool.py") as f:
            content = f.read()
        self.assertIn("validation/summary_quality_scores/entry", content,
                      "pdbe_api_tool.py fallback must use validation/summary_quality_scores/entry")
        self.assertNotIn("pdb/entry/quality", content,
                         "Old /pdb/entry/quality/ path must be removed from pdbe_api_tool.py")


# ---------------------------------------------------------------------------
# Feature-72A-007: PROSITE signature_name always None
# ---------------------------------------------------------------------------
class TestPROSITESignatureName(unittest.TestCase):
    """Feature-72A-007: PROSITE _scan_sequence used m.get('signature_id') which ScanProsite never returns."""

    def test_prosite_no_longer_uses_signature_id(self):
        """prosite_tool.py must not use 'signature_id' (not in ScanProsite API response)."""
        with open(SRC_ROOT / "tooluniverse" / "prosite_tool.py") as f:
            content = f.read()
        self.assertNotIn('"signature_name": m.get("signature_id")', content,
                         "PROSITE must not use signature_id (not returned by ScanProsite API)")

    def test_prosite_scan_result_structure(self):
        """Scan results must not include a null signature_name field from a nonexistent key."""
        from tooluniverse.prosite_tool import PROSITETool

        config = {
            "name": "PROSITE_scan_sequence",
            "type": "PROSITETool",
            "parameter": {"type": "object", "properties": {}, "required": []},
            "fields": {"endpoint": "scan_sequence"},
        }
        tool = PROSITETool(config)

        mock_scanprosite_response = {
            "n_match": 2,
            "matchset": [
                {
                    "signature_ac": "PS00001",
                    "start": 5,
                    "stop": 25,
                    "score": "0",
                    "level": "0",
                },
                {
                    "signature_ac": "PS50011",
                    "start": 30,
                    "stop": 80,
                    "score": "18.542",
                    "level": "0",
                },
            ],
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_scanprosite_response

        with patch("requests.post", return_value=mock_response):
            result = tool.run({"sequence": "ACDEFGHIKLMNPQRSTVWYACDEFGHIKLMNPQRSTVWY"})

        self.assertIn("data", result)
        matches = result["data"]
        self.assertEqual(len(matches), 2)
        # signature_accession must be populated
        self.assertEqual(matches[0]["signature_accession"], "PS00001")
        self.assertEqual(matches[1]["signature_accession"], "PS50011")
        # signature_name must NOT be present (removed since ScanProsite never returns signature_id)
        self.assertNotIn("signature_name", matches[0],
                         "signature_name must be removed since ScanProsite never returns signature_id")


# ---------------------------------------------------------------------------
# Feature-72A-010: DisProt wrong base URL (missing www.)
# ---------------------------------------------------------------------------
class TestDisProtBaseURL(unittest.TestCase):
    """Feature-72A-010: DisProt used disprot.org (no www.) which is unreachable."""

    def test_disprot_base_url_has_www(self):
        """DISPROT_BASE_URL must include www. prefix."""
        with open(SRC_ROOT / "tooluniverse" / "disprot_tool.py") as f:
            content = f.read()
        self.assertIn("www.disprot.org", content,
                      "disprot_tool.py must use www.disprot.org (not bare disprot.org)")

    def test_disprot_base_url_constant(self):
        """DISPROT_BASE_URL constant must be https://www.disprot.org/api."""
        import importlib
        import tooluniverse.disprot_tool as d
        importlib.reload(d)
        self.assertEqual(d.DISPROT_BASE_URL, "https://www.disprot.org/api")

    def test_disprot_error_message_correct_domain(self):
        """Connection error message must reference www.disprot.org."""
        with open(SRC_ROOT / "tooluniverse" / "disprot_tool.py") as f:
            content = f.read()
        # Should have updated error message
        self.assertIn("www.disprot.org", content)

    def test_disprot_search_calls_correct_url(self):
        """DisProt search must call www.disprot.org/api/search."""
        from tooluniverse.disprot_tool import DisProtTool

        config = {
            "name": "DisProt_search",
            "type": "DisProtTool",
            "parameter": {"type": "object", "properties": {}, "required": []},
            "fields": {"endpoint": "search"},
        }
        tool = DisProtTool(config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [], "pagination": {}}

        with patch("requests.get", return_value=mock_response) as mock_get:
            tool.run({"query": "TP53"})

        call_url = mock_get.call_args[0][0]
        self.assertIn("www.disprot.org", call_url,
                      f"DisProt search URL '{call_url}' must use www.disprot.org")
        self.assertNotIn("://disprot.org", call_url,
                         f"DisProt URL must not use bare disprot.org without www.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
