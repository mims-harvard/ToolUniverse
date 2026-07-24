"""Deeper disease-ontology tools (mocked HTTP).

Two confirmed, keyless capability gaps:

* ``HPO_get_disease_annotations`` — disease-keyed HPO annotation returning MAxO
  curated medical actions (treatments / management with TREATS / PREVENTS
  relations + target phenotypes), phenotypes grouped by body system, and the
  associated genes, for an OMIM / ORPHA / DECIPHER disease ID. Endpoint:
  ontology.jax.org/api/network/annotation/{disease-id}.
* ``MonarchV3_phenotype_profile_compare`` — pairwise phenotype-profile-to-profile
  semantic similarity for two explicit HPO term sets. Endpoint:
  api.monarchinitiative.org/v3/api/semsim/compare/{subjects}/{objects}.

Both tools reuse the existing ``HPOTool`` / ``MonarchV3Tool`` classes via the
``fields.endpoint`` dispatch mechanism (no new registration).
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------------- #
# HPO_get_disease_annotations
# --------------------------------------------------------------------------- #

_HPO_ANNOTATION = {
    "disease": {
        "id": "OMIM:154700",
        "name": "Marfan syndrome",
        "mondoId": "MONDO:0007947",
        "description": "A disorder of the connective tissue.",
    },
    "categories": {
        "Cardiovascular": [
            {
                "id": "HP:0002616",
                "name": "Aortic root aneurysm",
                "metadata": {"frequency": "20/30", "onset": ""},
                "category": "Cardiovascular",
            },
            {
                "id": "HP:0001659",
                "name": "Aortic regurgitation",
                "metadata": {"frequency": "", "onset": ""},
                "category": "Cardiovascular",
            },
        ],
        "Eye": [
            {
                "id": "HP:0000518",
                "name": "Cataract",
                "metadata": {"frequency": "", "onset": ""},
                "category": "Eye",
            },
        ],
    },
    "genes": [{"id": "NCBIGene:2200", "name": "FBN1"}],
    "medicalActions": [
        {
            "id": "MAXO:0000653",
            "name": "angiotensin receptor blocker therapy",
            "relations": ["PREVENTS", "TREATS"],
            "targets": [{"id": "HP:0002616", "name": "Aortic root aneurysm"}],
        },
        {
            "id": "MAXO:0000004",
            "name": "surgical procedure",
            "relations": ["TREATS"],
            "targets": [],
        },
    ],
}


def _hpo_tool():
    from tooluniverse.hpo_tool import HPOTool

    return HPOTool(
        {
            "name": "HPO_get_disease_annotations",
            "type": "HPOTool",
            "fields": {"endpoint": "get_disease_annotations"},
        }
    )


def _hpo_resp():
    r = MagicMock()
    r.status_code = 200
    r.raise_for_status.return_value = None
    r.json.return_value = _HPO_ANNOTATION
    return r


class TestHPODiseaseAnnotations(unittest.TestCase):
    def test_parses_medical_actions_categories_and_genes(self):
        """MAxO actions, body-system categories, and genes are parsed."""
        tool = _hpo_tool()
        with patch(
            "tooluniverse.hpo_tool.requests.get", return_value=_hpo_resp()
        ) as get:
            result = tool.run({"disease_id": "OMIM:154700"})

        # hits the disease-keyed network-annotation endpoint
        self.assertIn(
            "network/annotation/OMIM:154700", get.call_args.args[0]
        )
        self.assertEqual(result["status"], "success")

        data = result["data"]
        self.assertEqual(data["disease"]["name"], "Marfan syndrome")
        self.assertEqual(data["disease"]["mondo_id"], "MONDO:0007947")

        # medical actions: MAxO id + relations + target phenotypes
        ma = data["medical_actions"]
        self.assertEqual(len(ma), 2)
        first = ma[0]
        self.assertEqual(first["id"], "MAXO:0000653")
        self.assertEqual(first["relations"], ["PREVENTS", "TREATS"])
        self.assertEqual(first["targets"][0]["id"], "HP:0002616")

        # categories grouped by body system, sorted by phenotype_count desc
        cats = data["categories"]
        self.assertEqual(cats[0]["body_system"], "Cardiovascular")
        self.assertEqual(cats[0]["phenotype_count"], 2)
        self.assertEqual(cats[0]["phenotypes"][0]["frequency"], "20/30")

        # genes
        self.assertEqual(data["genes"], [{"id": "NCBIGene:2200", "name": "FBN1"}])

        meta = result["metadata"]
        self.assertEqual(meta["total_medical_actions"], 2)
        self.assertEqual(meta["total_body_systems"], 2)
        self.assertEqual(meta["total_phenotypes"], 3)
        self.assertEqual(meta["total_genes"], 1)

    def test_missing_disease_id_errors_without_network_call(self):
        """Missing disease_id returns an error and makes no HTTP call."""
        tool = _hpo_tool()
        with patch("tooluniverse.hpo_tool.requests.get") as get:
            result = tool.run({})
        self.assertEqual(result["status"], "error")
        get.assert_not_called()

    def test_unknown_disease_returns_error_not_raise(self):
        """A 404 from JAX yields a structured error, never a raise."""
        tool = _hpo_tool()
        r = MagicMock()
        r.status_code = 404
        with patch("tooluniverse.hpo_tool.requests.get", return_value=r):
            result = tool.run({"disease_id": "OMIM:99999999"})
        self.assertEqual(result["status"], "error")
        self.assertIn("OMIM:99999999", result["error"])


# --------------------------------------------------------------------------- #
# MonarchV3_phenotype_profile_compare
# --------------------------------------------------------------------------- #

_MONARCH_COMPARE = {
    "subject_termset": {
        "HP:0001250": {"id": "HP:0001250", "label": "Seizure"},
        "HP:0004322": {"id": "HP:0004322", "label": "Short stature"},
    },
    "object_termset": {
        "HP:0001263": {"id": "HP:0001263", "label": "Global developmental delay"},
        "HP:0000252": {"id": "HP:0000252", "label": "Microcephaly"},
    },
    "subject_best_matches": {
        "HP:0001250": {
            "match_source": "HP:0001250",
            "match_source_label": "Seizure",
            "match_target": "HP:0001263",
            "match_target_label": "Global developmental delay",
            "score": 8.033700937127838,
            "similarity": {
                "ancestor_id": "HP:0012638",
                "ancestor_label": "Abnormal nervous system physiology",
                "jaccard_similarity": 0.6,
                "phenodigm_score": 2.1955000711174444,
            },
        },
    },
    "object_best_matches": {
        "HP:0000252": {
            "match_source": "HP:0000252",
            "match_source_label": "Microcephaly",
            "match_target": "HP:0001250",
            "match_target_label": "Seizure",
            "score": 7.206856026369558,
            "similarity": {
                "ancestor_id": "HP:0012443",
                "ancestor_label": "Abnormality of brain morphology",
                "jaccard_similarity": 0.5,
                "phenodigm_score": 1.9,
            },
        },
    },
    "average_score": 8.158779564555921,
    "best_score": 8.697280647363142,
    "metric": "AncestorInformationContent",
}


def _monarch_tool():
    from tooluniverse.monarch_v3_tool import MonarchV3Tool

    return MonarchV3Tool(
        {
            "name": "MonarchV3_phenotype_profile_compare",
            "type": "MonarchV3Tool",
            "fields": {"endpoint": "semsim_compare"},
        }
    )


def _monarch_resp():
    r = MagicMock()
    r.status_code = 200
    r.raise_for_status.return_value = None
    r.json.return_value = _MONARCH_COMPARE
    return r


class TestMonarchProfileCompare(unittest.TestCase):
    def test_parses_scores_and_best_matches(self):
        """Overall scores and per-direction best matches are parsed."""
        tool = _monarch_tool()
        with patch(
            "tooluniverse.monarch_v3_tool.requests.get",
            return_value=_monarch_resp(),
        ) as get:
            result = tool.run(
                {
                    "subjects": ["HP:0001250", "HP:0004322"],
                    "objects": ["HP:0001263", "HP:0000252"],
                }
            )

        # term sets land in the path in order
        url = get.call_args.args[0]
        self.assertIn(
            "semsim/compare/HP:0001250,HP:0004322/HP:0001263,HP:0000252", url
        )
        self.assertEqual(result["status"], "success")

        data = result["data"]
        self.assertEqual(data["average_score"], 8.158779564555921)
        self.assertEqual(data["best_score"], 8.697280647363142)
        self.assertEqual(data["metric"], "AncestorInformationContent")

        sbm = data["subject_best_matches"]
        self.assertEqual(len(sbm), 1)
        m = sbm[0]
        self.assertEqual(m["query_phenotype"], "HP:0001250")
        self.assertEqual(m["matched_phenotype"], "HP:0001263")
        self.assertAlmostEqual(m["score"], 8.033700937127838)
        self.assertEqual(m["ancestor_id"], "HP:0012638")
        self.assertEqual(m["jaccard_similarity"], 0.6)
        self.assertAlmostEqual(m["phenodigm_score"], 2.1955000711174444)

        self.assertEqual(len(data["object_best_matches"]), 1)
        self.assertEqual(result["metadata"]["subjects"], ["HP:0001250", "HP:0004322"])

    def test_accepts_comma_separated_string(self):
        """Comma-separated string term sets are accepted like lists."""
        tool = _monarch_tool()
        with patch(
            "tooluniverse.monarch_v3_tool.requests.get",
            return_value=_monarch_resp(),
        ) as get:
            result = tool.run(
                {"subjects": "HP:0001250, HP:0004322", "objects": "HP:0001263"}
            )
        self.assertEqual(result["status"], "success")
        self.assertIn(
            "semsim/compare/HP:0001250,HP:0004322/HP:0001263", get.call_args.args[0]
        )

    def test_missing_termset_errors_without_network_call(self):
        """A missing subjects/objects set errors without any HTTP call."""
        tool = _monarch_tool()
        with patch("tooluniverse.monarch_v3_tool.requests.get") as get:
            r1 = tool.run({"objects": ["HP:0001263"]})
            r2 = tool.run({"subjects": ["HP:0001250"]})
        self.assertEqual(r1["status"], "error")
        self.assertEqual(r2["status"], "error")
        get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
