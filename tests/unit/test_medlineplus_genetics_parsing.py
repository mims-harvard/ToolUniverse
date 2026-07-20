"""Regression guard for Fix-R25A-1 (three compounding bugs) in
MedlinePlusRESTTool's genetics condition/gene lookups.

1. Case-sensitive URL: MedlinePlus's gene download endpoint serves real
   JSON for a lowercase gene symbol ("fbn1.json") but silently serves XML
   for an uppercase one ("FBN1.json") despite the .json extension --
   confirmed live. Gene symbols are naturally uppercase (FBN1), so every
   gene lookup was silently forced down a much buggier XML-fallback path.
   Fixed by lowercasing gene/condition values before building the URL.

2. get_list_items() only handled the XML-parsed dict shape ({item_key:
   [...]}), not the real-JSON list-of-wrapper-dicts shape ([{item_key:
   {...}}, ...]) -- so "genes" was always [] for condition lookups.
   Separately it mutated the list it was iterating, duplicating every
   entry once the XML-dict shape was hit.

3. The gene handler read `response.get("gene-summary", {})`, but real
   JSON gene responses have no "gene-summary" wrapper -- their fields are
   at the top level, same as condition responses. That always evaluated
   to {}, so every field was silently empty once the case-sensitivity fix
   routed gene lookups through real JSON.

Also added the "inheritance" field to the condition response, which was
present in the raw upstream JSON but never extracted at all.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.medlineplus_tool import MedlinePlusRESTTool

pytestmark = pytest.mark.unit

_CONDITION_JSON = {
    "name": "Marfan syndrome",
    "ghr_page": "https://medlineplus.gov/genetics/condition/marfan-syndrome",
    "text-list": [
        {
            "text": {
                "text-role": "description",
                "html": "<p>A connective tissue disorder.</p>",
            }
        }
    ],
    "inheritance-pattern-list": [
        {"inheritance-pattern": {"code": "ad", "memo": "Autosomal dominant"}}
    ],
    "related-gene-list": [
        {
            "related-gene": {
                "gene-symbol": "FBN1",
                "ghr-page": "https://medlineplus.gov/genetics/gene/fbn1",
            }
        }
    ],
    "synonym-list": [{"synonym": "Marfan's syndrome"}, {"synonym": "MFS"}],
}

_GENE_JSON = {
    "gene-symbol": "FBN1",
    "name": "fibrillin 1",
    "ghr-page": "https://medlineplus.gov/genetics/gene/fbn1",
    "text-list": [
        {"text": {"text-role": "function", "html": "<p>Makes fibrillin-1.</p>"}}
    ],
    "related-health-condition-list": [
        {
            "related-health-condition": {
                "name": "Marfan syndrome",
                "ghr-page": "https://medlineplus.gov/genetics/condition/marfan-syndrome",
            }
        },
        {
            "related-health-condition": {
                "name": "Weill-Marchesani syndrome",
                "ghr-page": "https://medlineplus.gov/genetics/condition/weill-marchesani-syndrome",
            }
        },
    ],
    "synonym-list": [{"synonym": "asprosin"}, {"synonym": "MASS"}],
}


def _tool_config(name):
    return {
        "name": name,
        "fields": {
            "endpoint": "https://medlineplus.gov/download/genetics/x/{gene_or_condition}.json"
        },
        "parameter": {"properties": {}},
    }


def _resp(json_body, text="{}"):
    r = MagicMock()
    r.status_code = 200
    r.json.return_value = json_body
    r.text = text
    return r


class TestConditionLookup:
    def test_genes_and_inheritance_extracted_from_real_json_list_shape(self):
        tool = MedlinePlusRESTTool(
            {
                "name": "MedlinePlus_get_genetics_condition_by_name",
                "fields": {
                    "endpoint": "https://medlineplus.gov/download/genetics/condition/{condition}.{format}"
                },
                "parameter": {"properties": {"format": {"default": "json"}}},
            }
        )
        resp = _resp(_CONDITION_JSON)

        with patch(
            "tooluniverse.medlineplus_tool.requests.get", return_value=resp
        ) as mock_get:
            result = tool.run({"condition": "Marfan-Syndrome"})

        called_url = mock_get.call_args[0][0]
        assert "marfan-syndrome" in called_url
        assert "Marfan-Syndrome" not in called_url
        assert result["genes"] == ["FBN1 (https://medlineplus.gov/genetics/gene/fbn1)"]
        assert result["inheritance"] == ["Autosomal dominant"]
        assert result["synonyms"] == ["Marfan's syndrome", "MFS"]


class TestGeneLookup:
    def test_gene_symbol_lowercased_in_url(self):
        tool = MedlinePlusRESTTool(
            {
                "name": "MedlinePlus_get_genetics_gene_by_name",
                "fields": {
                    "endpoint": "https://medlineplus.gov/download/genetics/gene/{gene}.{format}"
                },
                "parameter": {"properties": {"format": {"default": "json"}}},
            }
        )
        resp = _resp(_GENE_JSON)

        with patch(
            "tooluniverse.medlineplus_tool.requests.get", return_value=resp
        ) as mock_get:
            result = tool.run({"gene": "FBN1"})

        called_url = mock_get.call_args[0][0]
        assert called_url.endswith("gene/fbn1.json")
        assert result["name"] == "fibrillin 1"
        assert result["function"] != ""

    def test_health_conditions_not_duplicated(self):
        tool = MedlinePlusRESTTool(
            {
                "name": "MedlinePlus_get_genetics_gene_by_name",
                "fields": {
                    "endpoint": "https://medlineplus.gov/download/genetics/gene/{gene}.{format}"
                },
                "parameter": {"properties": {"format": {"default": "json"}}},
            }
        )
        resp = _resp(_GENE_JSON)

        with patch("tooluniverse.medlineplus_tool.requests.get", return_value=resp):
            result = tool.run({"gene": "FBN1"})

        assert result["health_conditions"] == [
            "Marfan syndrome (https://medlineplus.gov/genetics/condition/marfan-syndrome)",
            "Weill-Marchesani syndrome (https://medlineplus.gov/genetics/condition/weill-marchesani-syndrome)",
        ]
        assert result["synonyms"] == ["asprosin", "MASS"]
