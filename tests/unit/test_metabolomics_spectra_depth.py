"""Metabolomics / spectra depth tools (mocked HTTP, no live calls).

Covers seven new tools that reuse existing tool classes:

MassBank (BaseRESTTool, config-driven via massbank_tools.json):
  - MassBank_spectral_similarity_search   (endpoint /records/search, extract_path=data)
  - MassBank_get_record_by_accession      (endpoint /records/{accession})
  - MassBank_search_records_advanced      (endpoint /records/search, extract_path=data)

Metabolomics Workbench (MetabolomicsWorkbenchTool):
  - MetabolomicsWorkbench_find_studies_by_phenotype (context=metstat)
  - MetabolomicsWorkbench_get_gene_protein          (context=gene_protein)

GNPS (GNPSTool):
  - GNPS_get_library_record        (endpoint_type=get_library_record)
  - GNPS_npclassifier_from_smiles  (endpoint_type=npclassifier)

Each tool gets a parse (success) test and an error-path test. No network.
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


def _json_resp(status_code, body, text=""):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = body
    r.text = text
    r.url = "https://example.test/url"
    r.headers = {"content-type": "application/json"}
    r.raise_for_status = MagicMock()
    return r


# --------------------------------------------------------------------------- #
# MassBank — BaseRESTTool, config-driven
# --------------------------------------------------------------------------- #
def _massbank_tool(name):
    import json
    import os
    from tooluniverse.base_rest_tool import BaseRESTTool

    cfg_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "src",
        "tooluniverse",
        "data",
        "massbank_tools.json",
    )
    with open(cfg_path) as fh:
        configs = json.load(fh)
    cfg = next(c for c in configs if c["name"] == name)
    return BaseRESTTool(cfg)


class TestMassBankSimilaritySearch(unittest.TestCase):
    def test_parses_ranked_cosine_hits(self):
        """Similarity search extracts ranked accession+score list under data."""
        body = {
            "data": [
                {"accession": "MSBNK-BAFG-CSL2311094669", "score": 0.978714},
                {"accession": "MSBNK-mFam-MC20_001301", "score": 0.97498083},
            ]
        }
        tool = _massbank_tool("MassBank_spectral_similarity_search")
        with patch("tooluniverse.base_rest_tool.request_with_retry") as req:
            req.return_value = _json_resp(200, body)
            result = tool.run(
                {
                    "peak_list": "138.0661;100,110.0712;40,195.0877;60",
                    "peak_list_threshold": 0.5,
                }
            )
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["data"]), 2)
        self.assertEqual(result["data"][0]["accession"], "MSBNK-BAFG-CSL2311094669")
        self.assertAlmostEqual(result["data"][0]["score"], 0.978714)
        # peak_list must reach the API as a query param
        sent_params = req.call_args.kwargs.get("params", {})
        self.assertIn("peak_list", sent_params)
        self.assertEqual(sent_params["peak_list_threshold"], 0.5)

    def test_http_error_returns_error_status(self):
        """A non-2xx response surfaces a structured error, never raises."""
        tool = _massbank_tool("MassBank_spectral_similarity_search")
        with patch("tooluniverse.base_rest_tool.request_with_retry") as req:
            req.return_value = _json_resp(500, {}, text="boom")
            result = tool.run({"peak_list": "100;1"})
        self.assertEqual(result["status"], "error")
        self.assertIn("error", result)


class TestMassBankGetRecord(unittest.TestCase):
    def test_parses_full_record(self):
        """Record fetch returns the compound block with external links."""
        body = {
            "accession": "MSBNK-Athens_Univ-AU276601",
            "title": "Caffeine; LC-ESI-QTOF; MS2; CE: 10 eV; R=35000; [M+H]+",
            "compound": {
                "names": ["Caffeine"],
                "formula": "C8H10N4O2",
                "mass": 194.0803756,
                "smiles": "CN1C=NC2=C1C(=O)N(C)C(=O)N2C",
                "link": [
                    {"database": "CAS", "identifier": "58-08-2"},
                    {"database": "CHEBI", "identifier": "CHEBI:27732"},
                ],
            },
        }
        tool = _massbank_tool("MassBank_get_record_by_accession")
        with patch("tooluniverse.base_rest_tool.request_with_retry") as req:
            req.return_value = _json_resp(200, body)
            result = tool.run({"accession": "MSBNK-Athens_Univ-AU276601"})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["compound"]["formula"], "C8H10N4O2")
        # accession is a PATH param -> must appear in the URL, not query params
        called_url = req.call_args.args[2]
        self.assertIn("MSBNK-Athens_Univ-AU276601", called_url)

    def test_http_error_returns_error_status(self):
        """A 404 surfaces a structured error, never raises."""
        tool = _massbank_tool("MassBank_get_record_by_accession")
        with patch("tooluniverse.base_rest_tool.request_with_retry") as req:
            req.return_value = _json_resp(404, {}, text="not found")
            result = tool.run({"accession": "MSBNK-DOES-NOT-EXIST"})
        self.assertEqual(result["status"], "error")


class TestMassBankAdvancedSearch(unittest.TestCase):
    def test_filters_passed_as_query_params(self):
        """Advanced search forwards each provided filter as a query param."""
        body = {"data": [{"accession": "MSBNK-BAFG-CSL2311094660", "atomcount": 24}]}
        tool = _massbank_tool("MassBank_search_records_advanced")
        with patch("tooluniverse.base_rest_tool.request_with_retry") as req:
            req.return_value = _json_resp(200, body)
            result = tool.run({"exact_mass": 194.0804, "mass_tolerance": 0.005})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"][0]["accession"], "MSBNK-BAFG-CSL2311094660")
        sent_params = req.call_args.kwargs.get("params", {})
        self.assertEqual(sent_params["exact_mass"], 194.0804)
        self.assertEqual(sent_params["mass_tolerance"], 0.005)
        # None-valued optional filters must NOT be sent
        self.assertNotIn("ion_mode", sent_params)

    def test_http_error_returns_error_status(self):
        """A 5xx surfaces a structured error, never raises."""
        tool = _massbank_tool("MassBank_search_records_advanced")
        with patch("tooluniverse.base_rest_tool.request_with_retry") as req:
            req.return_value = _json_resp(500, {}, text="err")
            result = tool.run({"exact_mass": 1.0})
        self.assertEqual(result["status"], "error")


# --------------------------------------------------------------------------- #
# Metabolomics Workbench — MetabolomicsWorkbenchTool
# --------------------------------------------------------------------------- #
class TestMWBFindStudiesByPhenotype(unittest.TestCase):
    def _tool(self):
        from tooluniverse.metabolomics_workbench_tool import (
            MetabolomicsWorkbenchTool,
        )

        return MetabolomicsWorkbenchTool(
            {
                "name": "MetabolomicsWorkbench_find_studies_by_phenotype",
                "type": "MetabolomicsWorkbenchTool",
                "fields": {"context": "metstat", "output_format": "json"},
            }
        )

    def test_parses_rows_into_study_list(self):
        """METSTAT Row1/Row2 dict is flattened to a study list with count."""
        body = {
            "Row1": {
                "study": "ST003897",
                "study_title": "Postprandial Plasma Lipidomic Changes",
                "species": "Human",
                "source": "Blood",
                "disease": "Diabetes",
            },
            "Row2": {
                "study": "ST003896",
                "study_title": "Postprandial Plasma Metabolomic Changes",
                "species": "Human",
                "source": "Blood",
                "disease": "Diabetes",
            },
        }
        import json as _json

        with patch("tooluniverse.metabolomics_workbench_tool.requests.get") as get:
            get.return_value = _json_resp(200, body, text=_json.dumps(body))
            result = self._tool().run(
                {"species": "Human", "source": "Blood", "disease": "Diabetes"}
            )
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["data"][0]["study"], "ST003897")
        # The 8 semicolon slots must be in the request URL
        called_url = get.call_args.args[0]
        self.assertIn("metstat/", called_url)
        self.assertEqual(called_url.count(";"), 7)

    def test_no_filter_returns_error(self):
        """At least one filter is required (no fully-unconstrained query)."""
        result = self._tool().run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("filter", result["error"].lower())


class TestMWBGeneProtein(unittest.TestCase):
    def _tool(self):
        from tooluniverse.metabolomics_workbench_tool import (
            MetabolomicsWorkbenchTool,
        )

        return MetabolomicsWorkbenchTool(
            {
                "name": "MetabolomicsWorkbench_get_gene_protein",
                "type": "MetabolomicsWorkbenchTool",
                "fields": {"context": "gene_protein", "output_format": "json"},
            }
        )

    def test_gene_lookup_parses_record(self):
        """entity='gene' hits the gene endpoint and returns a 1-item list."""
        body = {
            "gene_symbol": "ACACA",
            "mgp_id": "MGP000016",
            "gene_id": "31",
            "gene_name": "acetyl-CoA carboxylase alpha",
            "map_location": "17q21",
        }
        import json as _json

        with patch("tooluniverse.metabolomics_workbench_tool.requests.get") as get:
            get.return_value = _json_resp(200, body, text=_json.dumps(body))
            result = self._tool().run(
                {"input_value": "acaca", "entity": "gene", "id_type": "gene_symbol"}
            )
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["data"][0]["gene_symbol"], "ACACA")
        called_url = get.call_args.args[0]
        self.assertIn("gene/gene_symbol/acaca/all", called_url)

    def test_protein_lookup_uses_protein_endpoint(self):
        """entity='protein' routes to the protein endpoint and flattens rows."""
        body = {
            "Row1": {
                "uniprot_id": "Q13085",
                "protein_entry": "ACACA_HUMAN",
                "mrna_id": "NM_198839",
                "refseq_id": "NP_942136",
                "seqlength": "2346",
            }
        }
        import json as _json

        with patch("tooluniverse.metabolomics_workbench_tool.requests.get") as get:
            get.return_value = _json_resp(200, body, text=_json.dumps(body))
            result = self._tool().run(
                {
                    "input_value": "Q13085",
                    "entity": "protein",
                    "id_type": "uniprot_id",
                }
            )
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"][0]["protein_entry"], "ACACA_HUMAN")
        called_url = get.call_args.args[0]
        self.assertIn("protein/uniprot_id/Q13085/all", called_url)

    def test_missing_input_value_returns_error(self):
        """Missing input_value yields a structured error."""
        result = self._tool().run({"entity": "gene"})
        self.assertEqual(result["status"], "error")


# --------------------------------------------------------------------------- #
# GNPS — GNPSTool
# --------------------------------------------------------------------------- #
class TestGNPSLibraryRecord(unittest.TestCase):
    def _tool(self):
        from tooluniverse.gnps_tool import GNPSTool

        return GNPSTool(
            {
                "name": "GNPS_get_library_record",
                "type": "GNPSTool",
                "fields": {"endpoint_type": "get_library_record"},
            }
        )

    def test_parses_annotation_block(self):
        """Library record flattens the first annotation into a compound record."""
        body = {
            "annotations": [
                {
                    "Compound_Name": "Lovastatin M+H; Mevinolin annotated in standard",
                    "Adduct": "M+H",
                    "Smiles": "CC[C@H](C)C(=O)O",
                    "INCHI": "InChI=1S/C24H36O5",
                    "Ion_Source": "LC-ESI",
                    "Instrument": "Orbitrap",
                    "PI": "Dorrestein",
                    "Ion_Mode": "Positive",
                    "Precursor_MZ": "405.264",
                    "SpectrumID": "CCMSLIB00005435737",
                }
            ],
            "spectruminfo": {"library_membership": "GNPS-LIBRARY", "ms_level": "2"},
        }
        with patch("tooluniverse.gnps_tool.requests.get") as get:
            get.return_value = _json_resp(200, body)
            result = self._tool().run({"spectrum_id": "CCMSLIB00005435737"})
        self.assertEqual(result["status"], "success")
        self.assertEqual(
            result["data"]["compound_name"],
            "Lovastatin M+H; Mevinolin annotated in standard",
        )
        self.assertEqual(result["data"]["adduct"], "M+H")
        self.assertEqual(result["data"]["library_membership"], "GNPS-LIBRARY")
        # SpectrumID forwarded as a query param
        self.assertEqual(
            get.call_args.kwargs["params"]["SpectrumID"], "CCMSLIB00005435737"
        )

    def test_empty_annotations_returns_error(self):
        """No annotation block -> structured error, not a bogus success."""
        with patch("tooluniverse.gnps_tool.requests.get") as get:
            get.return_value = _json_resp(200, {"annotations": []})
            result = self._tool().run({"spectrum_id": "CCMSLIB00000000000"})
        self.assertEqual(result["status"], "error")

    def test_missing_spectrum_id_returns_error(self):
        """Missing spectrum_id yields a structured error."""
        result = self._tool().run({})
        self.assertEqual(result["status"], "error")


class TestGNPSNPClassifier(unittest.TestCase):
    def _tool(self):
        from tooluniverse.gnps_tool import GNPSTool

        return GNPSTool(
            {
                "name": "GNPS_npclassifier_from_smiles",
                "type": "GNPSTool",
                "fields": {"endpoint_type": "npclassifier"},
            }
        )

    def test_parses_pathway_superclass_class(self):
        """NP Classifier result maps to class/superclass/pathway lists."""
        body = {
            "class_results": ["Purine alkaloids"],
            "superclass_results": ["Pseudoalkaloids"],
            "pathway_results": ["Alkaloids"],
            "isglycoside": False,
        }
        with patch("tooluniverse.gnps_tool.requests.get") as get:
            get.return_value = _json_resp(200, body)
            result = self._tool().run({"smiles": "CN1C=NC2=C1C(=O)N(C)C(=O)N2C"})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["class"], ["Purine alkaloids"])
        self.assertEqual(result["data"]["superclass"], ["Pseudoalkaloids"])
        self.assertEqual(result["data"]["pathway"], ["Alkaloids"])
        self.assertFalse(result["data"]["is_glycoside"])
        self.assertEqual(
            get.call_args.kwargs["params"]["smiles"], "CN1C=NC2=C1C(=O)N(C)C(=O)N2C"
        )

    def test_unclassifiable_returns_error(self):
        """All-empty result lists -> structured error."""
        body = {
            "class_results": [],
            "superclass_results": [],
            "pathway_results": [],
            "isglycoside": None,
        }
        with patch("tooluniverse.gnps_tool.requests.get") as get:
            get.return_value = _json_resp(200, body)
            result = self._tool().run({"smiles": "X"})
        self.assertEqual(result["status"], "error")

    def test_missing_smiles_returns_error(self):
        """Missing smiles yields a structured error."""
        result = self._tool().run({})
        self.assertEqual(result["status"], "error")


if __name__ == "__main__":
    unittest.main()
