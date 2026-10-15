"""The GWAS Catalog retired its v1 REST API; those URLs now answer HTTP 410.

gwas_get_snps_for_gene called v1 findByGene and failed on every gene. The
trait resolver's first tier called v1 findByEfoTrait, so every exact trait
name ("type 2 diabetes mellitus") fell through to the study fallback, which
could not settle on one term and errored. Both now use v2.
"""

from unittest.mock import patch

import pytest

from tooluniverse.gwas_tool import GWASAssociationsForTrait, GWASSNPsForGene

pytestmark = pytest.mark.unit


class _Response:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


def test_snps_for_gene_queries_v2_by_mapped_gene():
    calls = []

    def fake_request(endpoint, params=None):
        calls.append((endpoint, dict(params or {})))
        return {
            "_embedded": {
                "snps": [
                    {"rs_id": "rs8176216", "mapped_genes": ["BRCA1"]},
                    {"rs_id": "rs8176216", "mapped_genes": ["BRCA1"]},
                    {"rs_id": "rs10445316", "mapped_genes": ["BRCA1"]},
                ]
            },
            "page": {"size": 3, "totalElements": 23, "totalPages": 8, "number": 0},
        }

    tool = GWASSNPsForGene({"name": "gwas_get_snps_for_gene"})
    with patch.object(GWASSNPsForGene, "_make_request", side_effect=fake_request):
        result = tool.run({"gene_symbol": "BRCA1", "size": 3})

    endpoint, params = calls[0]
    assert endpoint == "/v2/single-nucleotide-polymorphisms"
    assert params["mapped_gene"] == "BRCA1"
    assert "geneName" not in params
    assert result["status"] == "success"
    assert [s["rs_id"] for s in result["data"]] == ["rs8176216", "rs10445316"]
    assert result["metadata"]["duplicates_removed"] == 1


def test_exact_trait_name_resolves_through_v2_efo_traits():
    seen = []

    def fake_get(url, params=None, timeout=None, **kwargs):
        seen.append(url)
        if url.endswith("/v2/efo-traits"):
            return _Response(
                {
                    "_embedded": {
                        "efo_traits": [
                            {
                                "efo_trait": "age of onset of type 2 diabetes mellitus",
                                "efo_id": "OBA_2001013",
                            },
                            {
                                "efo_trait": "type 2 diabetes mellitus",
                                "efo_id": "MONDO_0005148",
                            },
                        ]
                    }
                }
            )
        if "findByEfoTrait" in url:
            return _Response({"error": "Gone"}, status_code=410)
        raise AssertionError(f"unexpected HTTP call: {url}")

    tool = GWASAssociationsForTrait({"name": "gwas_get_associations_for_trait"})
    with patch("tooluniverse.gwas_tool.requests.get", side_effect=fake_get):
        resolved = tool._resolve_trait_to_efo("Type 2 Diabetes Mellitus")

    assert resolved["efo_id"] == "MONDO_0005148"
    assert resolved["efo_label"] == "type 2 diabetes mellitus"
    assert not any("findByEfoTrait" in u for u in seen)


def test_substring_matches_are_not_taken_as_exact():
    def fake_get(url, params=None, timeout=None, **kwargs):
        if url.endswith("/v2/efo-traits"):
            return _Response(
                {
                    "_embedded": {
                        "efo_traits": [
                            {"efo_trait": "T2-high asthma", "efo_id": "MONDO_0956975"}
                        ]
                    }
                }
            )
        if url.endswith("/v2/studies"):
            return _Response({"_embedded": {"studies": []}})
        raise AssertionError(f"unexpected HTTP call: {url}")

    tool = GWASAssociationsForTrait({"name": "gwas_get_associations_for_trait"})
    with patch("tooluniverse.gwas_tool.requests.get", side_effect=fake_get):
        assert tool._resolve_trait_to_efo("asthma") is None


@pytest.mark.network
def test_live_snps_for_brca1():
    result = GWASSNPsForGene({"name": "gwas_get_snps_for_gene"}).run(
        {"gene_symbol": "BRCA1", "size": 5}
    )
    assert result["status"] == "success", result
    assert result["data"]
    assert all("BRCA1" in (s.get("mapped_genes") or []) for s in result["data"])
