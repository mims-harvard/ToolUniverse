"""EBI Proteins API depth-feature tools (reverse/specialized lookups).

Covers five tools that reuse existing EBI Proteins tool classes:

- EBIProteins_get_rna_editing          (EBIProteinsExtTool, /rna-editing)
- EBIProteins_get_variation_by_dbsnp   (EBIProteinsExtTool, /variation/dbsnp)
- EBIProteins_get_variation_by_hgvs    (EBIProteinsExtTool, /variation/hgvs)
- EBIProteins_get_hpp_peptides         (EBIProteinsExtTool, /proteomics/hpp)
- EBIProteins_get_proteins_by_genomic_loc
                                       (EBIProteinsCoordinatesTool, /coordinates/glocation)

Each tool is exercised with mocked HTTP for both the parse path (real-shaped
payload) and an error path (HTTP failure / missing required argument). No
network access; the live EBI endpoints were verified separately.
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


def _resp(payload, status_code=200, raise_exc=None):
    """Build a mock requests.Response-like object."""
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = payload
    r.url = "https://www.ebi.ac.uk/proteins/api/mock"
    if raise_exc is not None:
        r.raise_for_status.side_effect = raise_exc
    else:
        r.raise_for_status.return_value = None
    return r


def _ext_tool(endpoint):
    from tooluniverse.ebi_proteins_ext_tool import EBIProteinsExtTool

    return EBIProteinsExtTool(
        {
            "name": f"ext_{endpoint}",
            "type": "EBIProteinsExtTool",
            "fields": {"endpoint": endpoint},
        }
    )


def _coord_tool(endpoint):
    from tooluniverse.ebi_proteins_coordinates_tool import EBIProteinsCoordinatesTool

    return EBIProteinsCoordinatesTool(
        {
            "name": f"coord_{endpoint}",
            "type": "EBIProteinsCoordinatesTool",
            "fields": {"endpoint": endpoint},
        }
    )


# ---------------------------------------------------------------------------
# RNA editing
# ---------------------------------------------------------------------------

RNA_EDITING_PAYLOAD = {
    "accession": "P42262",
    "entryName": "GRIA2_HUMAN",
    "features": [
        {
            "type": "rna_editing",
            "variantType": {
                "genomicLocation": ["NC_000004.12:g.157336723A>G"],
                "variantLocation": [
                    {
                        "loc": "p.Gln607Arg",
                        "seqId": "ENST00000264426.14",
                        "source": "Ensembl",
                    }
                ],
                "codon": "cGg",
                "consequenceType": "missense",
                "wildType": "Q",
                "mutatedType": "R",
                "somaticStatus": False,
            },
            "rnaEditingInfo": {"nsamples": 2280},
            "locationType": {"position": {"position": 607, "status": "certain"}},
        }
    ],
}


class TestRnaEditing(unittest.TestCase):
    def test_parse_qr_recoding_site(self):
        """Parse the canonical GRIA2 Q/R RNA-editing site at residue 607."""
        tool = _ext_tool("rna_editing")
        with patch(
            "tooluniverse.ebi_proteins_ext_tool.requests.get",
            return_value=_resp(RNA_EDITING_PAYLOAD),
        ):
            result = tool.run({"accession": "P42262"})

        self.assertEqual(result["status"], "success")
        data = result["data"]
        self.assertEqual(data["accession"], "P42262")
        self.assertEqual(data["total_sites"], 1)
        site = data["rna_editing_sites"][0]
        self.assertEqual(site["position"], 607)
        self.assertEqual(site["wild_type"], "Q")
        self.assertEqual(site["mutated_type"], "R")
        self.assertEqual(site["consequence_type"], "missense")
        self.assertEqual(site["genomic_location"], ["NC_000004.12:g.157336723A>G"])

    def test_missing_accession_is_error(self):
        tool = _ext_tool("rna_editing")
        result = tool.run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("accession", result["error"])

    def test_http_error_does_not_raise(self):
        """An HTTP 404 is returned as a status=error dict, not raised."""
        import requests

        tool = _ext_tool("rna_editing")
        err = requests.exceptions.HTTPError(response=MagicMock(status_code=404))
        with patch(
            "tooluniverse.ebi_proteins_ext_tool.requests.get",
            return_value=_resp(None, status_code=404, raise_exc=err),
        ):
            result = tool.run({"accession": "NOPE"})
        self.assertEqual(result["status"], "error")


# ---------------------------------------------------------------------------
# Variation by dbSNP / HGVS (shared list-of-entries shape)
# ---------------------------------------------------------------------------

VARIATION_PAYLOAD = [
    {
        "accession": "P04637",
        "entryName": "P53_HUMAN",
        "proteinName": "Cellular tumor antigen p53",
        "geneName": "TP53",
        "taxid": 9606,
        "features": [
            {
                "type": "VARIANT",
                "ftId": "VAR_045786",
                "wildType": "P",
                "alternativeSequence": "L",
                "begin": "72",
                "end": "72",
                "genomicLocation": ["NC_000017.11:g.7676154G>A"],
                "consequenceType": "missense",
                "clinicalSignificances": [{"type": "Benign"}],
                "xrefs": [
                    {
                        "name": "ClinVar",
                        "id": "RCV000164487",
                        "url": "https://www.ncbi.nlm.nih.gov/clinvar/RCV000164487",
                    }
                ],
            }
        ],
    },
    {
        "accession": "A0AAQ5BHX5",
        "entryName": "A0AAQ5BHX5_HUMAN",
        "taxid": 9606,
        "features": [],
    },
]


class TestVariationByDbsnp(unittest.TestCase):
    def test_parse_entries(self):
        """Parse the list of UniProt entries returned for a dbSNP rsID."""
        tool = _ext_tool("variation_dbsnp")
        with patch(
            "tooluniverse.ebi_proteins_ext_tool.requests.get",
            return_value=_resp(VARIATION_PAYLOAD),
        ):
            result = tool.run({"dbsnp_id": "rs1042522"})

        self.assertEqual(result["status"], "success")
        data = result["data"]
        self.assertEqual(data["dbsnp_id"], "rs1042522")
        self.assertEqual(data["total_entries"], 2)
        accs = [e["accession"] for e in data["entries"]]
        self.assertIn("P04637", accs)
        self.assertIn("A0AAQ5BHX5", accs)
        tp53 = next(e for e in data["entries"] if e["accession"] == "P04637")
        feat = tp53["features"][0]
        self.assertEqual(feat["wild_type"], "P")
        self.assertEqual(feat["alternative_sequence"], "L")
        self.assertEqual(feat["begin"], "72")

    def test_rsid_alias(self):
        """'rsid' is accepted as an alias for 'dbsnp_id'."""
        tool = _ext_tool("variation_dbsnp")
        with patch(
            "tooluniverse.ebi_proteins_ext_tool.requests.get",
            return_value=_resp(VARIATION_PAYLOAD),
        ):
            result = tool.run({"rsid": "rs1042522"})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["dbsnp_id"], "rs1042522")

    def test_missing_id_is_error(self):
        tool = _ext_tool("variation_dbsnp")
        result = tool.run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("dbsnp_id", result["error"])


class TestVariationByHgvs(unittest.TestCase):
    def test_parse_pro72leu_consequence(self):
        """Parse the TP53 Pro72Leu protein consequence for an HGVS query."""
        tool = _ext_tool("variation_hgvs")
        with patch(
            "tooluniverse.ebi_proteins_ext_tool.requests.get",
            return_value=_resp(VARIATION_PAYLOAD),
        ):
            result = tool.run({"hgvs": "NC_000017.11:g.7676154G>A"})

        self.assertEqual(result["status"], "success")
        data = result["data"]
        self.assertEqual(data["hgvs"], "NC_000017.11:g.7676154G>A")
        tp53 = next(e for e in data["entries"] if e["accession"] == "P04637")
        feat = tp53["features"][0]
        self.assertEqual(feat["wild_type"], "P")
        self.assertEqual(feat["alternative_sequence"], "L")
        self.assertEqual(feat["genomic_location"], ["NC_000017.11:g.7676154G>A"])

    def test_missing_hgvs_is_error(self):
        tool = _ext_tool("variation_hgvs")
        result = tool.run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("hgvs", result["error"])


# ---------------------------------------------------------------------------
# HPP peptides
# ---------------------------------------------------------------------------

HPP_PAYLOAD = {
    "accession": "P04637",
    "entryName": "P53_HUMAN",
    "features": [
        {
            "type": "HPP",
            "begin": "183",
            "end": "195",
            "peptide": "SDSDGLAPPQHLI",
            "unique": True,
            "evidences": [
                {
                    "code": "ECO:0007829",
                    "source": {"name": "HppPeptideAtlas", "id": "PAp1"},
                }
            ],
        }
    ],
}


class TestHppPeptides(unittest.TestCase):
    def test_parse_hpp_peptide(self):
        """Parse an HPP peptide feature (sequence, position, uniqueness)."""
        tool = _ext_tool("proteomics_hpp")
        with patch(
            "tooluniverse.ebi_proteins_ext_tool.requests.get",
            return_value=_resp(HPP_PAYLOAD),
        ):
            result = tool.run({"accession": "P04637"})

        self.assertEqual(result["status"], "success")
        data = result["data"]
        self.assertEqual(data["accession"], "P04637")
        self.assertEqual(data["total_peptides"], 1)
        pep = data["peptides"][0]
        self.assertEqual(pep["type"], "HPP")
        self.assertEqual(pep["peptide"], "SDSDGLAPPQHLI")
        self.assertEqual(pep["position_start"], "183")
        self.assertTrue(pep["unique"])
        self.assertEqual(pep["evidences"][0]["source"], "HppPeptideAtlas")

    def test_missing_accession_is_error(self):
        tool = _ext_tool("proteomics_hpp")
        result = tool.run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("accession", result["error"])


# ---------------------------------------------------------------------------
# Reverse genome -> protein lookup (glocation)
# ---------------------------------------------------------------------------

GLOCATION_PAYLOAD = [
    {
        "locations": [
            {
                "accession": "P04637",
                "entryType": "Swiss-Prot",
                "taxid": 9606,
                "ensemblGeneId": "ENSG00000141510",
                "ensemblTranscriptId": "ENST00000923569",
                "ensemblTranslationId": "ENSP00000593628",
                "proteinStart": 72,
                "proteinEnd": 72,
                "aminoAcids": "Pro",
                "chromosome": "17",
                "geneStart": 7676154,
                "geneEnd": 7676154,
                "reverseStrand": True,
                "assemblyName": "GRCh38",
            }
        ]
    }
]


class TestProteinsByGenomicLoc(unittest.TestCase):
    def test_parse_location_string(self):
        """Parse overlapping proteins from a 'chr:pos' genomic location."""
        tool = _coord_tool("glocation")
        with patch(
            "tooluniverse.ebi_proteins_coordinates_tool.requests.get",
            return_value=_resp(GLOCATION_PAYLOAD),
        ):
            result = tool.run({"taxonomy": "9606", "location": "17:7676154"})

        self.assertEqual(result["status"], "success")
        data = result["data"]
        self.assertEqual(data["location"], "17:7676154")
        self.assertEqual(data["total_proteins"], 1)
        p = data["proteins"][0]
        self.assertEqual(p["accession"], "P04637")
        self.assertEqual(p["ensembl_gene_id"], "ENSG00000141510")
        self.assertEqual(p["protein_start"], 72)
        self.assertEqual(p["amino_acids"], "Pro")
        self.assertEqual(p["chromosome"], "17")

    def test_chromosome_position_combine(self):
        """Separate chromosome+position combine into the glocation URL."""
        tool = _coord_tool("glocation")
        with patch(
            "tooluniverse.ebi_proteins_coordinates_tool.requests.get",
            return_value=_resp(GLOCATION_PAYLOAD),
        ) as mock_get:
            result = tool.run({"chromosome": "17", "position": 7676154})

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["location"], "17:7676154")
        # Default taxonomy 9606 must be in the URL.
        called_url = mock_get.call_args[0][0]
        self.assertIn("/glocation/9606/17:7676154", called_url)

    def test_missing_location_is_error(self):
        """Missing location/chromosome returns an error, not a raise."""
        tool = _coord_tool("glocation")
        result = tool.run({"taxonomy": "9606"})
        self.assertEqual(result["status"], "error")
        self.assertIn("location", result["error"])

    def test_http_error_does_not_raise(self):
        """An HTTP 404 is returned as a status=error dict, not raised."""
        import requests

        tool = _coord_tool("glocation")
        err = requests.exceptions.HTTPError(response=MagicMock(status_code=404))
        with patch(
            "tooluniverse.ebi_proteins_coordinates_tool.requests.get",
            return_value=_resp(None, status_code=404, raise_exc=err),
        ):
            result = tool.run({"location": "17:1"})
        self.assertEqual(result["status"], "error")


if __name__ == "__main__":
    unittest.main()
