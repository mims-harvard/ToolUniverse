"""Regression guard for Fix-R26D-1: OpenGenesGeneTool's "disease_categories"
field was always empty for every gene tested. Confirmed live (curl to
open-genes.com/api/gene/LMNA): diseaseCategories entries key their label
as "icdCategoryName", not "name" -- the shared _names() helper (which
looks for "name") never matched, silently discarding real curated disease
evidence (e.g. LMNA/progeria, confirmed present via
evidence_counts.geneAssociatedWithProgeriaSyndromes: 3). Also added a new
"diseases" field surfacing the separate, more specific named-disease list
(e.g. "Progeria", "Dilated cardiomyopathy") that the raw API already
provides under "diseases" but the tool never read at all.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.open_genes_tool import OpenGenesGeneTool

pytestmark = pytest.mark.unit

_LMNA_RESPONSE = {
    "symbol": "LMNA",
    "name": "lamin A/C",
    "ncbiId": 4000,
    "diseaseCategories": [
        {"id": 336, "icdCode": "I30-I52", "icdCategoryName": "Other forms of heart disease"},
        {"id": 772, "icdCode": "G60-G64", "icdCategoryName": "Polyneuropathies and other disorders of the peripheral nervous system"},
    ],
    "diseases": [
        {"id": 33, "icdCode": "I42.0", "name": "Dilated cardiomyopathy"},
        {"id": 37, "icdCode": "Q87.5", "name": "Mandibuloacral dysplasia with lipodystrophy"},
        {"id": 40, "icdCode": "E34.8", "name": "Progeria"},
    ],
    "agingMechanisms": [],
    "functionalClusters": [],
    "researches": {},
}


def _tool():
    return OpenGenesGeneTool({"name": "opengenes_test", "fields": {}})


def _resp(json_body):
    r = MagicMock()
    r.raise_for_status = MagicMock()
    r.json.return_value = json_body
    return r


class TestDiseaseFieldExtraction:
    def test_disease_categories_extracted_from_icd_category_name(self):
        tool = _tool()
        resp = _resp(_LMNA_RESPONSE)

        with patch("tooluniverse.open_genes_tool.requests.get", return_value=resp):
            result = tool.run({"symbol": "LMNA"})

        assert result["status"] == "success"
        assert result["data"]["disease_categories"] == [
            "Other forms of heart disease",
            "Polyneuropathies and other disorders of the peripheral nervous system",
        ]

    def test_diseases_field_populated(self):
        tool = _tool()
        resp = _resp(_LMNA_RESPONSE)

        with patch("tooluniverse.open_genes_tool.requests.get", return_value=resp):
            result = tool.run({"symbol": "LMNA"})

        assert result["data"]["diseases"] == [
            "Dilated cardiomyopathy",
            "Mandibuloacral dysplasia with lipodystrophy",
            "Progeria",
        ]

    def test_empty_disease_lists_do_not_crash(self):
        tool = _tool()
        response = dict(_LMNA_RESPONSE)
        response["diseaseCategories"] = []
        response["diseases"] = []
        resp = _resp(response)

        with patch("tooluniverse.open_genes_tool.requests.get", return_value=resp):
            result = tool.run({"symbol": "LMNA"})

        assert result["data"]["disease_categories"] == []
        assert result["data"]["diseases"] == []
