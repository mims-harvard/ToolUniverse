"""Drug-target-deep depth tools: parse + error-path coverage (mocked HTTP).

Covers twelve new tools that close confirmed drug-target / variant depth gaps:

Pharos (PharosTool, GraphQL):
* ``Pharos_get_target_ligands``       — per-target ligand/drug bioactivities.
* ``Pharos_get_ligand_targets``       — drug -> all protein targets (reverse PGx).
* ``Pharos_get_target_expression``    — GTEx baseline tissue TPM for a target.

OpenTargets platform (OpenTarget, GraphQL):
* ``OpenTargets_get_target_expression_by_ensemblID`` — RNA+protein baseline.
* ``OpenTargets_get_target_pathways_by_ensemblID``   — Reactome membership.
* ``OpenTargets_get_target_depmap_essentiality``     — DepMap CRISPR essentiality.
* ``OpenTargets_get_target_prioritisation``          — 16 prioritisation metrics.
* ``OpenTargets_get_target_cancer_hallmarks``        — cancer hallmarks.
* ``OpenTargets_get_variant_effect_predictions``     — VEP/SIFT/AlphaMissense.
* ``OpenTargets_get_variant_transcript_consequences`` — per-transcript impact.
* ``OpenTargets_get_variant_pharmacogenomics``       — variant PGx (PharmGKB).
* ``OpenTargets_get_credible_set_colocalisation``    — GWAS/QTL colocalisation.

All network calls are mocked; these tests never touch the live APIs.
"""

import json
import os
import unittest
from unittest.mock import patch, MagicMock

import pytest

pytestmark = pytest.mark.unit


_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "src",
    "tooluniverse",
    "data",
)


def _load_config(filename, tool_name):
    """Load a single tool config dict by name from a data JSON file."""
    with open(os.path.join(_DATA_DIR, filename)) as fh:
        tools = json.load(fh)
    for cfg in tools:
        if cfg.get("name") == tool_name:
            return cfg
    raise AssertionError(f"{tool_name} not found in {filename}")


def _mock_post(payload):
    """Build a MagicMock standing in for requests.post returning ``payload``."""
    resp = MagicMock()
    resp.ok = True
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json.return_value = payload
    return resp


# ---------------------------------------------------------------------------
# Pharos tools (PharosTool dispatches on fields.operation)
# ---------------------------------------------------------------------------


def _pharos_tool(tool_name):
    from tooluniverse.pharos_tool import PharosTool

    return PharosTool(_load_config("pharos_tools.json", tool_name))


_PHAROS_LIGANDS = {
    "data": {
        "target": {
            "sym": "DRD2",
            "tdl": "Tclin",
            "fam": "GPCR",
            "ligandCounts": [
                {"name": "ligand", "value": 3210},
                {"name": "drug", "value": 81},
            ],
            "ligands": [
                {
                    "name": "Pipamazine",
                    "isdrug": True,
                    "synonyms": [{"name": "ChEMBL", "value": "CHEMBL12345"}],
                    "activities": [{"type": "IC50", "moa": None, "value": 8.74}],
                }
            ],
        }
    }
}

_PHAROS_LIGAND_TARGETS = {
    "data": {
        "ligand": {
            "name": "haloperidol",
            "isdrug": True,
            "smiles": "Fc1ccc(cc1)C(=O)CCC",
            "targetCount": 19,
            "activities": [
                {
                    "target": {"sym": "DRD2", "tdl": "Tclin", "fam": "GPCR"},
                    "type": "",
                    "value": 8.3,
                    "moa": None,
                }
            ],
        }
    }
}

_PHAROS_EXPRESSION = {
    "data": {
        "target": {
            "sym": "DRD2",
            "gtex": [
                {"tissue": "Pituitary", "tpm": 89.735, "gender": None},
                {"tissue": "Brain - Substantia nigra", "tpm": 14.12, "gender": None},
            ],
        }
    }
}


class TestPharosTargetLigands(unittest.TestCase):
    def test_parses_ligand_counts_and_activities(self):
        """ligandCounts and ligand activities parse correctly."""
        tool = _pharos_tool("Pharos_get_target_ligands")
        with patch("tooluniverse.pharos_tool.requests.post") as post:
            post.return_value = _mock_post(_PHAROS_LIGANDS)
            result = tool.run({"gene": "DRD2", "top": 3})

        self.assertEqual(result["status"], "success")
        data = result["data"]
        self.assertEqual(data["sym"], "DRD2")
        counts = {c["name"]: c["value"] for c in data["ligandCounts"]}
        self.assertEqual(counts["ligand"], 3210)
        self.assertEqual(counts["drug"], 81)
        self.assertEqual(data["ligands"][0]["name"], "Pipamazine")
        self.assertEqual(data["ligands"][0]["activities"][0]["type"], "IC50")
        self.assertEqual(data["ligands"][0]["activities"][0]["value"], 8.74)

    def test_missing_identifier_is_error(self):
        """Missing gene/uniprot identifier returns an error envelope."""
        tool = _pharos_tool("Pharos_get_target_ligands")
        result = tool.run({})  # neither gene nor uniprot
        self.assertEqual(result["status"], "error")
        self.assertIn("error", result)

    def test_graphql_error_returns_error_status(self):
        """A GraphQL errors payload maps to status=error."""
        tool = _pharos_tool("Pharos_get_target_ligands")
        with patch("tooluniverse.pharos_tool.requests.post") as post:
            post.return_value = _mock_post({"errors": [{"message": "boom"}]})
            result = tool.run({"gene": "DRD2"})
        self.assertEqual(result["status"], "error")


class TestPharosLigandTargets(unittest.TestCase):
    def test_parses_target_count_and_activities(self):
        """Ligand targetCount and per-target activities parse correctly."""
        tool = _pharos_tool("Pharos_get_ligand_targets")
        with patch("tooluniverse.pharos_tool.requests.post") as post:
            post.return_value = _mock_post(_PHAROS_LIGAND_TARGETS)
            result = tool.run({"ligid": "Haloperidol"})

        self.assertEqual(result["status"], "success")
        data = result["data"]
        self.assertEqual(data["targetCount"], 19)
        act = data["activities"][0]
        self.assertEqual(act["target"]["sym"], "DRD2")
        self.assertEqual(act["target"]["tdl"], "Tclin")
        self.assertEqual(act["value"], 8.3)

    def test_missing_ligid_is_error(self):
        """Missing ligid returns an error envelope."""
        tool = _pharos_tool("Pharos_get_ligand_targets")
        result = tool.run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("error", result)

    def test_request_exception_returns_error(self):
        """A network RequestException maps to status=error."""
        import requests as _rq

        tool = _pharos_tool("Pharos_get_ligand_targets")
        with patch("tooluniverse.pharos_tool.requests.post") as post:
            post.side_effect = _rq.exceptions.RequestException("down")
            result = tool.run({"ligid": "Haloperidol"})
        self.assertEqual(result["status"], "error")


class TestPharosTargetExpression(unittest.TestCase):
    def test_parses_gtex_records_with_count(self):
        """GTEx tissue records parse with a count field."""
        tool = _pharos_tool("Pharos_get_target_expression")
        with patch("tooluniverse.pharos_tool.requests.post") as post:
            post.return_value = _mock_post(_PHAROS_EXPRESSION)
            result = tool.run({"gene": "DRD2"})

        self.assertEqual(result["status"], "success")
        data = result["data"]
        self.assertEqual(data["sym"], "DRD2")
        self.assertEqual(data["count"], 2)
        by_tissue = {g["tissue"]: g["tpm"] for g in data["gtex"]}
        self.assertEqual(by_tissue["Pituitary"], 89.735)

    def test_missing_identifier_is_error(self):
        """Missing gene/uniprot identifier returns an error envelope."""
        tool = _pharos_tool("Pharos_get_target_expression")
        result = tool.run({})
        self.assertEqual(result["status"], "error")


# ---------------------------------------------------------------------------
# OpenTargets platform tools (OpenTarget runs query_schema via execute_query)
# ---------------------------------------------------------------------------


def _ot_tool(filename, tool_name):
    from tooluniverse.graphql_tool import OpentargetTool

    return OpentargetTool(_load_config(filename, tool_name))


_OT_FILE = "opentarget_tools.json"
_OTG_FILE = "opentarget_genetics_tools.json"


_OT_EXPRESSION = {
    "data": {
        "target": {
            "id": "ENSG00000146648",
            "approvedSymbol": "EGFR",
            "expressions": [
                {
                    "tissue": {"label": "macrophage", "organs": ["immune organ"]},
                    "rna": {"value": 0, "zscore": -1, "level": -1},
                    "protein": {"level": -1},
                }
            ],
        }
    }
}

_OT_PATHWAYS = {
    "data": {
        "target": {
            "id": "ENSG00000146648",
            "approvedSymbol": "EGFR",
            "pathways": [
                {
                    "pathwayId": "R-HSA-9009391",
                    "pathway": "Extra-nuclear estrogen signaling",
                    "topLevelTerm": "Signal Transduction",
                }
            ],
        }
    }
}

_OT_DEPMAP = {
    "data": {
        "target": {
            "id": "ENSG00000146648",
            "approvedSymbol": "EGFR",
            "isEssential": False,
            "depMapEssentiality": [
                {
                    "tissueName": "craniocervical region",
                    "screens": [
                        {
                            "depmapId": "ACH-001691",
                            "cellLineName": "UPCI-SCC-029A",
                            "geneEffect": 0.02,
                            "expression": 6.18,
                        }
                    ],
                }
            ],
        }
    }
}

_OT_PRIORITISATION = {
    "data": {
        "target": {
            "id": "ENSG00000146648",
            "approvedSymbol": "EGFR",
            "prioritisation": {
                "items": [
                    {"key": "geneticConstraint", "value": "-0.713"},
                    {"key": "hasPocket", "value": "1"},
                ]
            },
        }
    }
}

_OT_HALLMARKS = {
    "data": {
        "target": {
            "id": "ENSG00000146648",
            "approvedSymbol": "EGFR",
            "hallmarks": {
                "cancerHallmarks": [
                    {
                        "label": "proliferative signalling",
                        "impact": "promotes",
                        "description": "EGFR drives proliferation",
                    }
                ],
                "attributes": [{"name": "oncogene", "description": "role in cancer"}],
            },
        }
    }
}

_OT_VARIANT_EFFECT = {
    "data": {
        "variant": {
            "id": "19_44908822_C_T",
            "variantEffect": [
                {"method": "VEP", "assessment": "missense_variant", "score": 0.68},
                {"method": "SIFT", "assessment": "deleterious", "score": 0},
            ],
        }
    }
}

_OT_TRANSCRIPT = {
    "data": {
        "variant": {
            "id": "19_44908822_C_T",
            "transcriptConsequences": [
                {
                    "transcriptId": "ENST00000647358",
                    "aminoAcidChange": None,
                    "consequenceScore": 0.2,
                    "impact": "MODIFIER",
                }
            ],
        }
    }
}

_OT_PGX = {
    "data": {
        "variant": {
            "id": "19_44908822_C_T",
            "pharmacogenomics": [
                {
                    "drugs": [{"drugFromSource": "warfarin"}],
                    "phenotypeText": "shorter duration to stable warfarin dose",
                    "evidenceLevel": "3",
                    "genotypeAnnotationText": "CT genotype carriers...",
                }
            ],
        }
    }
}

_OT_COLOC = {
    "data": {
        "credibleSet": {
            "studyLocusId": "0004aaf4841475f0caf5bcde04432bcf",
            "colocalisation": {
                "count": 2217,
                "rows": [
                    {
                        "colocalisationMethod": "COLOC_PIP_ECAVIAR",
                        "h4": 0.9996,
                        "clpp": 0.683,
                        "numberColocalisingVariants": 1,
                        "otherStudyLocus": {"studyLocusId": "2e9c48b52c"},
                    }
                ],
            },
        }
    }
}


class TestOpenTargetExpression(unittest.TestCase):
    def test_parses_rna_and_protein(self):
        """RNA and protein expression records parse correctly."""
        tool = _ot_tool(_OT_FILE, "OpenTargets_get_target_expression_by_ensemblID")
        with patch("tooluniverse.graphql_tool.requests.post") as post:
            post.return_value = _mock_post(_OT_EXPRESSION)
            result = tool.run({"ensemblId": "ENSG00000146648"})

        self.assertEqual(result["status"], "success")
        target = result["data"]["target"]
        self.assertEqual(target["approvedSymbol"], "EGFR")
        first = target["expressions"][0]
        self.assertEqual(first["tissue"]["label"], "macrophage")
        self.assertEqual(first["rna"]["zscore"], -1)
        self.assertEqual(first["protein"]["level"], -1)

    def test_api_failure_returns_error(self):
        """A non-200 HTTP response maps to status=error."""
        tool = _ot_tool(_OT_FILE, "OpenTargets_get_target_expression_by_ensemblID")
        with patch("tooluniverse.graphql_tool.requests.post") as post:
            resp = MagicMock()
            resp.ok = False
            resp.status_code = 500
            resp.text = "server error"
            post.return_value = resp
            result = tool.run({"ensemblId": "ENSG00000146648"})
        self.assertEqual(result["status"], "error")


class TestOpenTargetPathways(unittest.TestCase):
    def test_parses_reactome_pathways(self):
        """Reactome pathway membership parses correctly."""
        tool = _ot_tool(_OT_FILE, "OpenTargets_get_target_pathways_by_ensemblID")
        with patch("tooluniverse.graphql_tool.requests.post") as post:
            post.return_value = _mock_post(_OT_PATHWAYS)
            result = tool.run({"ensemblId": "ENSG00000146648"})

        self.assertEqual(result["status"], "success")
        pw = result["data"]["target"]["pathways"][0]
        self.assertEqual(pw["pathwayId"], "R-HSA-9009391")
        self.assertEqual(pw["topLevelTerm"], "Signal Transduction")

    def test_graphql_error_returns_error(self):
        """A GraphQL errors payload maps to status=error."""
        tool = _ot_tool(_OT_FILE, "OpenTargets_get_target_pathways_by_ensemblID")
        with patch("tooluniverse.graphql_tool.requests.post") as post:
            post.return_value = _mock_post({"errors": [{"message": "bad"}]})
            result = tool.run({"ensemblId": "ENSG00000146648"})
        self.assertEqual(result["status"], "error")


class TestOpenTargetDepMap(unittest.TestCase):
    def test_parses_essentiality(self):
        """DepMap per-tissue essentiality and screens parse correctly."""
        tool = _ot_tool(_OT_FILE, "OpenTargets_get_target_depmap_essentiality")
        with patch("tooluniverse.graphql_tool.requests.post") as post:
            post.return_value = _mock_post(_OT_DEPMAP)
            result = tool.run({"ensemblId": "ENSG00000146648"})

        self.assertEqual(result["status"], "success")
        target = result["data"]["target"]
        self.assertEqual(target["isEssential"], False)
        tissue = target["depMapEssentiality"][0]
        self.assertEqual(tissue["tissueName"], "craniocervical region")
        self.assertEqual(tissue["screens"][0]["depmapId"], "ACH-001691")

    def test_no_data_returns_error(self):
        """A response without a data key maps to status=error."""
        tool = _ot_tool(_OT_FILE, "OpenTargets_get_target_depmap_essentiality")
        with patch("tooluniverse.graphql_tool.requests.post") as post:
            post.return_value = _mock_post({"notdata": {}})
            result = tool.run({"ensemblId": "ENSG00000146648"})
        self.assertEqual(result["status"], "error")


class TestOpenTargetPrioritisation(unittest.TestCase):
    def test_parses_items(self):
        """Prioritisation key/value items parse correctly."""
        tool = _ot_tool(_OT_FILE, "OpenTargets_get_target_prioritisation")
        with patch("tooluniverse.graphql_tool.requests.post") as post:
            post.return_value = _mock_post(_OT_PRIORITISATION)
            result = tool.run({"ensemblId": "ENSG00000146648"})

        self.assertEqual(result["status"], "success")
        items = result["data"]["target"]["prioritisation"]["items"]
        by_key = {i["key"]: i["value"] for i in items}
        self.assertEqual(by_key["geneticConstraint"], "-0.713")
        self.assertEqual(by_key["hasPocket"], "1")

    def test_graphql_error_returns_error(self):
        """A GraphQL errors payload maps to status=error."""
        tool = _ot_tool(_OT_FILE, "OpenTargets_get_target_prioritisation")
        with patch("tooluniverse.graphql_tool.requests.post") as post:
            post.return_value = _mock_post({"errors": [{"message": "x"}]})
            result = tool.run({"ensemblId": "ENSG00000146648"})
        self.assertEqual(result["status"], "error")


class TestOpenTargetHallmarks(unittest.TestCase):
    def test_parses_hallmarks_and_attributes(self):
        """Cancer hallmarks and attributes parse correctly."""
        tool = _ot_tool(_OT_FILE, "OpenTargets_get_target_cancer_hallmarks")
        with patch("tooluniverse.graphql_tool.requests.post") as post:
            post.return_value = _mock_post(_OT_HALLMARKS)
            result = tool.run({"ensemblId": "ENSG00000146648"})

        self.assertEqual(result["status"], "success")
        hm = result["data"]["target"]["hallmarks"]
        self.assertEqual(hm["cancerHallmarks"][0]["impact"], "promotes")
        self.assertEqual(hm["cancerHallmarks"][0]["label"], "proliferative signalling")
        self.assertEqual(hm["attributes"][0]["name"], "oncogene")

    def test_graphql_error_returns_error(self):
        """A GraphQL errors payload maps to status=error."""
        tool = _ot_tool(_OT_FILE, "OpenTargets_get_target_cancer_hallmarks")
        with patch("tooluniverse.graphql_tool.requests.post") as post:
            post.return_value = _mock_post({"errors": [{"message": "x"}]})
            result = tool.run({"ensemblId": "ENSG00000146648"})
        self.assertEqual(result["status"], "error")


class TestOpenTargetVariantEffect(unittest.TestCase):
    def test_parses_effects(self):
        """Per-method variant effect predictions parse correctly."""
        tool = _ot_tool(_OTG_FILE, "OpenTargets_get_variant_effect_predictions")
        with patch("tooluniverse.graphql_tool.requests.post") as post:
            post.return_value = _mock_post(_OT_VARIANT_EFFECT)
            result = tool.run({"variantId": "19_44908822_C_T"})

        self.assertEqual(result["status"], "success")
        effects = result["data"]["variant"]["variantEffect"]
        by_method = {e["method"]: e for e in effects}
        self.assertEqual(by_method["VEP"]["assessment"], "missense_variant")
        self.assertEqual(by_method["VEP"]["score"], 0.68)
        self.assertEqual(by_method["SIFT"]["assessment"], "deleterious")

    def test_api_failure_returns_error(self):
        """A non-200 HTTP response maps to status=error."""
        tool = _ot_tool(_OTG_FILE, "OpenTargets_get_variant_effect_predictions")
        with patch("tooluniverse.graphql_tool.requests.post") as post:
            resp = MagicMock()
            resp.ok = False
            resp.status_code = 500
            resp.text = "err"
            post.return_value = resp
            result = tool.run({"variantId": "19_44908822_C_T"})
        self.assertEqual(result["status"], "error")


class TestOpenTargetTranscriptConsequences(unittest.TestCase):
    def test_parses_transcript_consequences(self):
        """Per-transcript consequences parse correctly."""
        tool = _ot_tool(_OTG_FILE, "OpenTargets_get_variant_transcript_consequences")
        with patch("tooluniverse.graphql_tool.requests.post") as post:
            post.return_value = _mock_post(_OT_TRANSCRIPT)
            result = tool.run({"variantId": "19_44908822_C_T"})

        self.assertEqual(result["status"], "success")
        tc = result["data"]["variant"]["transcriptConsequences"][0]
        self.assertEqual(tc["transcriptId"], "ENST00000647358")
        self.assertEqual(tc["impact"], "MODIFIER")

    def test_graphql_error_returns_error(self):
        """A GraphQL errors payload maps to status=error."""
        tool = _ot_tool(_OTG_FILE, "OpenTargets_get_variant_transcript_consequences")
        with patch("tooluniverse.graphql_tool.requests.post") as post:
            post.return_value = _mock_post({"errors": [{"message": "x"}]})
            result = tool.run({"variantId": "19_44908822_C_T"})
        self.assertEqual(result["status"], "error")


class TestOpenTargetVariantPGx(unittest.TestCase):
    def test_parses_pharmacogenomics(self):
        """Variant pharmacogenomics records parse correctly."""
        tool = _ot_tool(_OTG_FILE, "OpenTargets_get_variant_pharmacogenomics")
        with patch("tooluniverse.graphql_tool.requests.post") as post:
            post.return_value = _mock_post(_OT_PGX)
            result = tool.run({"variantId": "19_44908822_C_T"})

        self.assertEqual(result["status"], "success")
        pgx = result["data"]["variant"]["pharmacogenomics"][0]
        self.assertEqual(pgx["drugs"][0]["drugFromSource"], "warfarin")
        self.assertEqual(pgx["evidenceLevel"], "3")
        self.assertIn("warfarin", pgx["phenotypeText"])

    def test_graphql_error_returns_error(self):
        """A GraphQL errors payload maps to status=error."""
        tool = _ot_tool(_OTG_FILE, "OpenTargets_get_variant_pharmacogenomics")
        with patch("tooluniverse.graphql_tool.requests.post") as post:
            post.return_value = _mock_post({"errors": [{"message": "x"}]})
            result = tool.run({"variantId": "19_44908822_C_T"})
        self.assertEqual(result["status"], "error")


class TestOpenTargetColocalisation(unittest.TestCase):
    def test_parses_colocalisation(self):
        """Credible-set colocalisation rows parse correctly."""
        tool = _ot_tool(_OTG_FILE, "OpenTargets_get_credible_set_colocalisation")
        with patch("tooluniverse.graphql_tool.requests.post") as post:
            post.return_value = _mock_post(_OT_COLOC)
            result = tool.run({"studyLocusId": "0004aaf4841475f0caf5bcde04432bcf"})

        self.assertEqual(result["status"], "success")
        coloc = result["data"]["credibleSet"]["colocalisation"]
        self.assertEqual(coloc["count"], 2217)
        row = coloc["rows"][0]
        self.assertEqual(row["colocalisationMethod"], "COLOC_PIP_ECAVIAR")
        self.assertAlmostEqual(row["h4"], 0.9996)
        self.assertAlmostEqual(row["clpp"], 0.683)

    def test_api_failure_returns_error(self):
        """A non-200 HTTP response maps to status=error."""
        tool = _ot_tool(_OTG_FILE, "OpenTargets_get_credible_set_colocalisation")
        with patch("tooluniverse.graphql_tool.requests.post") as post:
            resp = MagicMock()
            resp.ok = False
            resp.status_code = 500
            resp.text = "err"
            post.return_value = resp
            result = tool.run({"studyLocusId": "0004aaf4841475f0caf5bcde04432bcf"})
        self.assertEqual(result["status"], "error")


if __name__ == "__main__":
    unittest.main()
