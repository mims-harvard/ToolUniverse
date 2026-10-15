"""Alliance allele tools returned every allele with null id/symbol.

``/gene/{id}/alleles`` nests the allele under ``allele`` and the variants under
``variantList``; the tools read ``id``/``symbol``/``symbolText`` from the record's top
level. ZFIN_get_gene_alleles therefore returned ``id: None, symbol: None,
symbol_text: None`` for all 22 zebrafish alleles of pax2a, and
Alliance_get_alleles_and_models had the same null symbol. Records below are trimmed
from the live responses for ZFIN:ZDB-GENE-990415-8 (curated alleles) and
FB:FBgn0004647 (variant-only records: ``allele`` holds just a ``curie``).
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.alliance_genome_tool import AllianceGenomeTool, _allele_summary

pytestmark = pytest.mark.unit

ZEBRAFISH = {
    "category": "allele_summary",
    "alterationType": "allele with one variant",
    "hasPhenotype": True,
    "hasDisease": False,
    "allele": {
        "type": "Allele",
        "primaryExternalId": "ZFIN:ZDB-ALT-980203-1592",
        "alleleSymbol": {"displayText": "th44"},
        "alleleSynonyms": [{"displayText": "H44A"}, {"displayText": "th44a"}],
    },
    "variantList": [
        {
            "type": "Variant",
            "variantType": {"name": "point_mutation"},
            "curatedVariantGenomicLocations": [
                {
                    "start": 33168303,
                    "end": 33168303,
                    "hgvs": "NC_133188.1:g.33168303G>T",
                    "variantGenomicLocationAssociationObject": {"name": "13"},
                    "mostSevereConsequence": {"name": "stop_gained"},
                }
            ],
        }
    ],
}
FLY_VARIANT = {
    "category": "allele_summary",
    "alterationType": "variant",
    "hasPhenotype": False,
    "hasDisease": False,
    "allele": {"type": "Variant", "curie": "FB:FBtr0070507.1:c.161-4308_161-4291del"},
    "variantList": [
        {
            "variantType": {"name": "deletion"},
            "curatedVariantGenomicLocations": [
                {"hgvs": "NC_004354.4:g.3143667_3143684del"}
            ],
        }
    ],
}


def test_curated_allele_keeps_its_id_symbol_synonyms_and_variant():
    row = _allele_summary(ZEBRAFISH)
    assert row["id"] == "ZFIN:ZDB-ALT-980203-1592"
    assert row["symbol"] == row["symbol_text"] == "th44"
    assert row["synonyms"] == ["H44A", "th44a"]
    assert row["alteration_type"] == "allele with one variant"
    assert row["has_phenotype"] is True and row["has_disease"] is False
    (variant,) = row["variants"]
    assert variant["type"] == "point_mutation"
    assert variant["name"] == "NC_133188.1:g.33168303G>T"
    assert variant["location"] == {
        "chromosome": "13",
        "start": 33168303,
        "end": 33168303,
        "hgvs": "NC_133188.1:g.33168303G>T",
    }
    assert variant["most_severe_consequence"] == "stop_gained"


def test_variant_only_record_uses_the_curie_as_its_id():
    row = _allele_summary(FLY_VARIANT)
    assert row["id"] == "FB:FBtr0070507.1:c.161-4308_161-4291del"
    assert row["symbol"] is None
    assert row["variants"][0]["type"] == "deletion"


def _tool(operation):
    return AllianceGenomeTool({"name": "x", "fields": {"endpoint_type": operation}})


def test_gene_alleles_tool_returns_flattened_alleles_and_the_total():
    response = MagicMock()
    response.json.return_value = {"total": 22, "results": [ZEBRAFISH, FLY_VARIANT]}
    with patch("tooluniverse.alliance_genome_tool.requests.get", return_value=response):
        result = _tool("gene_alleles").run({"gene_id": "ZFIN:ZDB-GENE-990415-8"})
    assert [a["id"] for a in result["data"]][0] == "ZFIN:ZDB-ALT-980203-1592"
    assert result["data"][0]["symbol"] == "th44"
    assert result["metadata"]["total_results"] == 22


def test_alleles_and_models_uses_the_same_fields():
    tool = _tool("gene_alleles_and_models")
    replies = {
        "alleles": {"total": 22, "results": [ZEBRAFISH]},
        "models": {"total": 0, "results": []},
    }
    with patch.object(
        tool, "_alliance_get", side_effect=lambda gid, kind, params: replies[kind]
    ):
        result = tool.run({"gene_id": "ZFIN:ZDB-GENE-990415-8"})
    (allele,) = result["data"]["alleles"]
    assert allele["allele_id"] == "ZFIN:ZDB-ALT-980203-1592"
    assert allele["symbol"] == "th44"
    assert allele["variant_locations"] == ["NC_133188.1:g.33168303G>T"]
