"""Protein-structure depth tools: parse + error-path coverage (mocked HTTP).

Covers four new tools that close confirmed residue/fold/motif/protonation
capability gaps in the protein-structure cluster. Each tool REUSES an existing
registered class (no new @register_tool):

* ``InterPro_get_residue_annotations`` (InterProRESTTool) — residue-level
  functional-site annotations (binding/active/PTM sites with exact residue
  positions) from the InterPro ``?residues`` endpoint.
* ``PDBeSIFTS_get_scop_mapping`` (PDBeSIFTSTool) — SCOP structural
  classification (class/fold/superfamily) with per-chain residue ranges from
  PDBe SIFTS ``/mappings/scop``.
* ``ELM_get_interaction_domains`` (ELMTool) — ELM motif-to-interaction-domain
  mapping (SLiM class -> recognizing Pfam domain) from ``interactiondomains.tsv``.
* ``ProteinsPlus_protonate_structure`` (ProteinsPlusRESTTool) — ProtoSS
  hydrogen/protonation placement (POST ``/protoss_rest`` then poll).

All network calls are mocked; these tests never touch the live APIs.
"""

import json
import unittest
from unittest.mock import patch, MagicMock

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Config loading helper (load the real JSON config for each new tool by name)
# ---------------------------------------------------------------------------

import os

_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "src",
    "tooluniverse",
    "data",
)


def _load_config(json_file: str, tool_name: str) -> dict:
    with open(os.path.join(_DATA_DIR, json_file)) as f:
        configs = json.load(f)
    for cfg in configs:
        if cfg.get("name") == tool_name:
            return cfg
    raise AssertionError(f"{tool_name} not found in {json_file}")


# ---------------------------------------------------------------------------
# InterPro_get_residue_annotations  (InterProRESTTool)
# ---------------------------------------------------------------------------

_INTERPRO_RESIDUES_FAKE = {
    "PIRSR000617-2": {
        "accession": "PIRSR000617-2",
        "name": "PIRSR000617-2",
        "source_database": "pirsr",
        "locations": [
            {
                "description": "BINDING: ATP",
                "fragments": [
                    {"start": 745, "end": 745, "residues": "K"},
                    {"start": 841, "end": 841, "residues": "R"},
                ],
            }
        ],
    },
    "PIRSR638784-1": {
        "accession": "PIRSR638784-1",
        "name": "PIRSR638784-1",
        "source_database": "pirsr",
        "locations": [
            {
                "description": "ACT_SITE: Proton acceptor.",
                "fragments": [{"start": 855, "end": 855, "residues": "D"}],
            }
        ],
    },
}


def _interpro_tool():
    from tooluniverse.interpro_tool import InterProRESTTool

    return InterProRESTTool(
        _load_config("interpro_tools.json", "InterPro_get_residue_annotations")
    )


class TestInterProResidueAnnotations(unittest.TestCase):
    def test_parse_residue_sites(self):
        """Residue-site entries are keyed by signature and keep exact positions."""
        tool = _interpro_tool()
        mock_resp = MagicMock()
        mock_resp.json.return_value = _INTERPRO_RESIDUES_FAKE
        mock_resp.raise_for_status.return_value = None

        with patch.object(tool.session, "get", return_value=mock_resp):
            result = tool.run({"protein_id": "P00533"})

        self.assertEqual(result["status"], "success")
        data = result["data"]
        # Keyed by signature accession
        self.assertIn("PIRSR000617-2", data)
        self.assertIn("PIRSR638784-1", data)
        # Exact binding-site residue positions preserved
        binding = data["PIRSR000617-2"]["locations"][0]
        self.assertEqual(binding["description"], "BINDING: ATP")
        frags = binding["fragments"]
        self.assertEqual(frags[0]["start"], 745)
        self.assertEqual(frags[0]["residues"], "K")
        self.assertEqual(frags[1]["start"], 841)
        self.assertEqual(frags[1]["residues"], "R")
        # Active-site residue
        act = data["PIRSR638784-1"]["locations"][0]
        self.assertEqual(act["description"], "ACT_SITE: Proton acceptor.")
        self.assertEqual(act["fragments"][0]["start"], 855)

    def test_url_template_substitution(self):
        """The {protein_id} placeholder is substituted into the residues URL."""
        tool = _interpro_tool()
        url = tool._build_url({"protein_id": "P00533"})
        self.assertIn("/protein/uniprot/P00533/", url)
        self.assertIn("residues", url)

    def test_error_path_never_raises(self):
        """A network failure is caught and returned as a status=error envelope."""
        tool = _interpro_tool()
        with patch.object(
            tool.session, "get", side_effect=RuntimeError("boom network")
        ):
            result = tool.run({"protein_id": "P00533"})
        self.assertEqual(result["status"], "error")
        self.assertIn("error", result)
        self.assertIn("boom network", result["error"])


# ---------------------------------------------------------------------------
# PDBeSIFTS_get_scop_mapping  (PDBeSIFTSTool)
# ---------------------------------------------------------------------------

_SCOP_FAKE = {
    "1cbs": {
        "SCOP": {
            "50847": {
                "class": {"description": "All beta proteins", "sunid": 48724},
                "fold": {"description": "Lipocalins", "sunid": 50813},
                "superfamily": {"description": "Lipocalins", "sunid": 50814},
                "description": "Fatty acid binding protein-like",
                "identifier": "Fatty acid binding protein-like",
                "sccs": "b.60.1.2",
                "mappings": [
                    {
                        "chain_id": "A",
                        "struct_asym_id": "A",
                        "entity_id": 1,
                        "scop_id": "d1cbsa_",
                        "start": {"residue_number": 1, "author_residue_number": 1},
                        "end": {"residue_number": 137, "author_residue_number": 137},
                    }
                ],
            }
        }
    }
}


def _scop_tool():
    from tooluniverse.pdbe_sifts_tool import PDBeSIFTSTool

    return PDBeSIFTSTool(
        _load_config("pdbe_sifts_tools.json", "PDBeSIFTS_get_scop_mapping")
    )


class TestPDBeSIFTSScopMapping(unittest.TestCase):
    def test_parse_scop_classification(self):
        """SCOP class/fold/superfamily and per-chain residue ranges are parsed."""
        tool = _scop_tool()
        mock_resp = MagicMock()
        mock_resp.json.return_value = _SCOP_FAKE
        mock_resp.raise_for_status.return_value = None

        with patch("tooluniverse.pdbe_sifts_tool.requests.get", return_value=mock_resp):
            result = tool.run({"pdb_id": "1CBS"})

        self.assertEqual(result["status"], "success")
        data = result["data"]
        self.assertEqual(data["pdb_id"], "1cbs")  # lowercased
        self.assertEqual(data["total_domains"], 1)
        dom = data["scop_domains"][0]
        self.assertEqual(dom["scop_sunid"], "50847")
        self.assertEqual(dom["class"], "All beta proteins")
        self.assertEqual(dom["fold"], "Lipocalins")
        self.assertEqual(dom["superfamily"], "Lipocalins")
        self.assertEqual(dom["sccs"], "b.60.1.2")
        # Per-chain residue range mapping
        m = dom["mappings"][0]
        self.assertEqual(m["chain_id"], "A")
        self.assertEqual(m["start_residue"], 1)
        self.assertEqual(m["end_residue"], 137)
        self.assertEqual(m["scop_id"], "d1cbsa_")

    def test_missing_pdb_id_error(self):
        """Missing pdb_id returns a structured error, not an exception."""
        tool = _scop_tool()
        result = tool.run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("pdb_id", result["error"])

    def test_error_path_never_raises(self):
        """A network failure is caught and returned as a status=error envelope."""
        tool = _scop_tool()
        with patch(
            "tooluniverse.pdbe_sifts_tool.requests.get",
            side_effect=RuntimeError("scop boom"),
        ):
            result = tool.run({"pdb_id": "1cbs"})
        self.assertEqual(result["status"], "error")
        self.assertIn("error", result)


# ---------------------------------------------------------------------------
# ELM_get_interaction_domains  (ELMTool)
# ---------------------------------------------------------------------------

_ELM_INTERACTION_TSV = (
    '"ELM identifier"\t"Interaction Domain Id"\t'
    '"Interaction Domain Description"\t"Interaction Domain Name"\n'
    '"CLV_NRD_NRD_1"\t"PF00675"\t"Peptidase_M16"\t'
    '"Insulinase (Peptidase family M16)"\n'
    '"CLV_PCSK_FUR_1"\t"PF00082"\t"Peptidase_S8"\t"Subtilase family"\n'
    '"DEG_APCC_DBOX_1"\t"PF00400"\t"WD40"\t"WD domain, G-beta repeat"\n'
)


def _elm_tool():
    from tooluniverse.elm_tool import ELMTool

    return ELMTool(_load_config("elm_tools.json", "ELM_get_interaction_domains"))


class TestELMInteractionDomains(unittest.TestCase):
    def _mock_resp(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = _ELM_INTERACTION_TSV
        return mock_resp

    def test_parse_all_mappings(self):
        """All motif-to-Pfam-domain mappings are parsed from the TSV."""
        tool = _elm_tool()
        with patch.object(tool.session, "get", return_value=self._mock_resp()):
            result = tool.run({"operation": "get_interaction_domains"})

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["metadata"]["total_mappings"], 3)
        rows = {r["elm_identifier"]: r for r in result["data"]}
        self.assertEqual(rows["CLV_NRD_NRD_1"]["pfam_accession"], "PF00675")
        self.assertEqual(
            rows["CLV_NRD_NRD_1"]["interaction_domain_description"], "Peptidase_M16"
        )
        self.assertEqual(rows["CLV_PCSK_FUR_1"]["pfam_accession"], "PF00082")
        self.assertEqual(
            rows["DEG_APCC_DBOX_1"]["interaction_domain_description"], "WD40"
        )

    def test_filter_by_elm_identifier(self):
        """elm_identifier filter returns only the matching motif class."""
        tool = _elm_tool()
        with patch.object(tool.session, "get", return_value=self._mock_resp()):
            result = tool.run(
                {
                    "operation": "get_interaction_domains",
                    "elm_identifier": "CLV_NRD_NRD_1",
                }
            )
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["data"]), 1)
        self.assertEqual(result["data"][0]["pfam_accession"], "PF00675")

    def test_filter_by_query(self):
        """Free-text query matches against Pfam accession and domain fields."""
        tool = _elm_tool()
        with patch.object(tool.session, "get", return_value=self._mock_resp()):
            result = tool.run(
                {"operation": "get_interaction_domains", "query": "PF00400"}
            )
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["data"]), 1)
        self.assertEqual(result["data"][0]["elm_identifier"], "DEG_APCC_DBOX_1")

    def test_http_error_path(self):
        """Non-200 HTTP status yields a structured error envelope."""
        tool = _elm_tool()
        bad = MagicMock()
        bad.status_code = 503
        with patch.object(tool.session, "get", return_value=bad):
            result = tool.run({"operation": "get_interaction_domains"})
        self.assertEqual(result["status"], "error")
        self.assertIn("503", result["error"])

    def test_exception_path_never_raises(self):
        """Transport exceptions are caught and returned as an error envelope."""
        tool = _elm_tool()
        with patch.object(tool.session, "get", side_effect=RuntimeError("elm boom")):
            result = tool.run({"operation": "get_interaction_domains"})
        self.assertEqual(result["status"], "error")
        self.assertIn("error", result)


# ---------------------------------------------------------------------------
# ProteinsPlus_protonate_structure  (ProteinsPlusRESTTool)
# ---------------------------------------------------------------------------


def _protoss_tool():
    from tooluniverse.proteinsplus_tool import ProteinsPlusRESTTool

    return ProteinsPlusRESTTool(
        _load_config("proteinsplus_tools.json", "ProteinsPlus_protonate_structure")
    )


class TestProteinsPlusProtonate(unittest.TestCase):
    def test_transform_params_pdb_code(self):
        """The /protoss_rest body must nest pdbCode under a 'protoss' key."""
        tool = _protoss_tool()
        body = tool._transform_params({"pdb_id": "1cbs"})
        self.assertEqual(body, {"protoss": {"pdbCode": "1cbs"}})

    def test_transform_params_pdb_content(self):
        """Raw PDB content maps to protoss.pdbData (not pdbCode)."""
        tool = _protoss_tool()
        body = tool._transform_params({"pdb_content": "HEADER ...\nATOM ..."})
        self.assertIn("protoss", body)
        self.assertEqual(body["protoss"]["pdbData"], "HEADER ...\nATOM ...")
        self.assertNotIn("pdbCode", body["protoss"])

    def test_transform_params_with_ligand(self):
        """Optional ligand content is forwarded as protoss.ligandData."""
        tool = _protoss_tool()
        body = tool._transform_params(
            {"pdb_content": "HEADER", "ligand_content": "LIGSDF"}
        )
        self.assertEqual(body["protoss"]["ligandData"], "LIGSDF")

    def test_submit_job_returns_location(self):
        """submit_job posts the nested body and returns the job location URL."""
        tool = _protoss_tool()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status_code": 200,
            "location": "https://proteins.plus/api/protoss_rest/ABC123",
        }
        with patch(
            "tooluniverse.proteinsplus_tool.requests.post", return_value=mock_resp
        ) as mock_post:
            location = tool.submit_job({"pdb_id": "1cbs"})
        self.assertEqual(location, "https://proteins.plus/api/protoss_rest/ABC123")
        # Verify the POST body was correctly nested
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["json"], {"protoss": {"pdbCode": "1cbs"}})

    def test_check_status_done_returns_result(self):
        """A completed poll yields protein/ligands/log result URLs."""
        tool = _protoss_tool()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status_code": 200,
            "protein": "https://proteins.plus/results/protoss/ABC123/1cbs.pdb",
            "ligands": "https://proteins.plus/results/protoss/ABC123/1cbs.sdf",
            "log": "https://proteins.plus/results/protoss/ABC123/1cbs_log.txt",
        }
        with patch(
            "tooluniverse.proteinsplus_tool.requests.get", return_value=mock_resp
        ):
            status = tool.check_status("https://proteins.plus/api/protoss_rest/ABC123")
        self.assertTrue(status["done"])
        result = status["result"]
        self.assertTrue(result["protein"].endswith("1cbs.pdb"))
        self.assertTrue(result["ligands"].endswith("1cbs.sdf"))
        self.assertTrue(result["log"].endswith("1cbs_log.txt"))

    def test_format_result_envelope(self):
        """format_result wraps the ProtoSS result in the standard envelope."""
        tool = _protoss_tool()
        out = tool.format_result(
            {
                "protein": "u.pdb",
                "ligands": "u.sdf",
                "log": "u.txt",
            }
        )
        self.assertEqual(out["status"], "success")
        self.assertEqual(out["data"]["protein"], "u.pdb")
        self.assertEqual(out["metadata"]["endpoint"], "/protoss_rest")

    def test_check_status_processing_not_done(self):
        """HTTP 202 means still running — must report not done, no exception."""
        tool = _protoss_tool()
        mock_resp = MagicMock()
        mock_resp.status_code = 202
        with patch(
            "tooluniverse.proteinsplus_tool.requests.get", return_value=mock_resp
        ):
            status = tool.check_status("https://proteins.plus/api/protoss_rest/ABC123")
        self.assertFalse(status["done"])


if __name__ == "__main__":
    unittest.main()
