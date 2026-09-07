"""Unit test: CIViC must not lose the curated record for gene-prefixed spellings.

Regression: clinical writing joins the gene symbol and the variant designation
into one token ("EGFRvIII", "BRAFV600E", "KRASG12C"), but CIViC stores the
variant under the bare designation ("VIII") and names its molecular profile
"<GENE> <designation>" ("EGFR VIII"). Every CIViC name filter is a
case-insensitive *substring* match, so the joined spelling could only ever reach
a differently-named record: `variant_name="EGFRvIII"` returned exactly one node
— an empty duplicate stub (id 1516, molecularProfileScore 0.0) — while the
curated record (id 312, "VIII", score 69.0, with variantTypes and
hgvsDescriptions) was silently dropped, and
`molecular_profile="EGFRvIII"` returned 1 of 6 evidence items.

The tool now also queries the gene-stripped designation whenever (and only
when) the input carries a gene prefix, merges both result sets de-duplicated by
id, and discloses the expansion in `normalization_note`.
"""

import glob
import json
from unittest.mock import patch

import pytest

from tooluniverse.civic_tool import CIViCTool, _split_gene_prefixed_name


def _load(name):
    for f in glob.glob("src/tooluniverse/data/*.json"):
        try:
            data = json.load(open(f))
        except ValueError:
            continue
        if isinstance(data, list):
            for tool in data:
                if isinstance(tool, dict) and tool.get("name") == name:
                    return tool
    raise AssertionError(f"tool config not found: {name}")


class _Resp:
    """Minimal stand-in for a requests.Response carrying a GraphQL payload."""

    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        pass


# --------------------------------------------------------------------------
# The split heuristic itself: general, no per-entity special cases.
# --------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    "name,expected",
    [
        ("EGFRvIII", ("EGFR", "vIII")),
        ("BRAFV600E", ("BRAF", "V600E")),
        ("KRASG12C", ("KRAS", "G12C")),
        ("TP53R175H", ("TP53", "R175H")),
        ("ERBB2V777L", ("ERBB2", "V777L")),
    ],
)
def test_gene_prefixed_spellings_split(name, expected):
    assert _split_gene_prefixed_name(name) == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    "name",
    [
        "BRAF V600E",  # already separated — CIViC matches it natively
        "EGFR VIII",
        "V600E",  # bare designation, no gene prefix
        "T790M",
        "ERBB2",  # a gene symbol carrying digits must never split
        "TP53",
        "EGFR",
        "EGFR Amplification",
        "BCR::ABL1 Fusion",
    ],
)
def test_non_prefixed_input_does_not_split(name):
    assert _split_gene_prefixed_name(name) is None


@pytest.mark.unit
def test_named_gene_makes_the_prefix_authoritative():
    assert _split_gene_prefixed_name("EGFRvIII", "EGFR") == ("EGFR", "vIII")
    assert _split_gene_prefixed_name("EGFR-vIII", "EGFR") == ("EGFR", "vIII")
    # Variant that does not start with the named gene is left alone.
    assert _split_gene_prefixed_name("L858R", "EGFR") is None
    # Gene symbol on its own leaves no designation behind.
    assert _split_gene_prefixed_name("EGFR", "EGFR") is None


# --------------------------------------------------------------------------
# civic_search_variants: gene_name + gene-prefixed variant_name
# --------------------------------------------------------------------------

_EGFR_VARIANTS = [
    {"id": 1516, "name": "EGFRVIII", "feature": {"id": 19, "name": "EGFR"}},
    {"id": 312, "name": "VIII", "feature": {"id": 19, "name": "EGFR"}},
    {"id": 33, "name": "L858R", "feature": {"id": 19, "name": "EGFR"}},
]

_BRAF_VARIANTS = [
    {"id": 12, "name": "V600E", "feature": {"id": 5, "name": "BRAF"}},
    {"id": 704, "name": "V600E+V600K", "feature": {"id": 5, "name": "BRAF"}},
    {"id": 250, "name": "AMPLIFICATION", "feature": {"id": 5, "name": "BRAF"}},
]


def _variants_transport(gene_id, gene_name, variants, calls):
    """Serve the gene-id lookup and the gene-variants page from a fixture."""

    def _post(url, json=None, **kwargs):
        calls.append(json)
        query = (json or {}).get("query", "")
        if "genes(entrezSymbols" in query:
            return _Resp(
                {"data": {"genes": {"nodes": [{"id": gene_id, "name": gene_name}]}}}
            )
        return _Resp(
            {
                "data": {
                    "gene": {
                        "id": gene_id,
                        "name": gene_name,
                        "variants": {
                            "nodes": list(variants),
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                        },
                    }
                }
            }
        )

    return _post


@pytest.mark.unit
def test_gene_prefixed_variant_name_returns_bare_designation_record():
    calls = []
    tool = CIViCTool(_load("civic_search_variants"))
    with patch(
        "tooluniverse.civic_tool.requests.post",
        side_effect=_variants_transport(19, "EGFR", _EGFR_VARIANTS, calls),
    ):
        result = tool.run({"gene_name": "EGFR", "variant_name": "EGFRvIII"})

    nodes = result["data"]["gene"]["variants"]["nodes"]
    ids = [n["id"] for n in nodes]
    # The curated record stored under the bare designation is no longer dropped...
    assert 312 in ids
    # ...and the same-spelled duplicate is still returned, not silently replaced.
    assert 1516 in ids
    # Unrelated variants of the same gene stay filtered out.
    assert 33 not in ids
    # The union is disclosed: both spellings are named.
    note = result.get("normalization_note", "")
    assert "EGFRvIII" in note and "vIII" in note
    assert "merged" in note


@pytest.mark.unit
def test_non_prefixed_variant_name_is_unchanged_and_costs_no_extra_query():
    calls = []
    tool = CIViCTool(_load("civic_search_variants"))
    with patch(
        "tooluniverse.civic_tool.requests.post",
        side_effect=_variants_transport(5, "BRAF", _BRAF_VARIANTS, calls),
    ):
        result = tool.run({"gene_name": "BRAF", "variant_name": "V600E"})

    ids = [n["id"] for n in result["data"]["gene"]["variants"]["nodes"]]
    assert ids == [12, 704]
    assert "normalization_note" not in result
    # Exactly the gene-id lookup + one variants page: no speculative extra call.
    assert len(calls) == 2


# --------------------------------------------------------------------------
# civic_search_evidence_items: gene-prefixed molecular_profile
# --------------------------------------------------------------------------


def _evidence_item(item_id, profile_name):
    return {
        "id": item_id,
        "description": "",
        "evidenceType": "PREDICTIVE",
        "significance": "SENSITIVITYRESPONSE",
        "status": "ACCEPTED",
        "disease": {"name": "Glioblastoma"},
        "therapies": [],
        "molecularProfile": {"id": 400, "name": profile_name},
    }


def _evidence_transport(by_profile, calls):
    def _post(url, json=None, **kwargs):
        profile = (json or {}).get("variables", {}).get("molecularProfileName")
        calls.append(profile)
        return _Resp(
            {"data": {"evidenceItems": {"nodes": list(by_profile.get(profile, []))}}}
        )

    return _post


@pytest.mark.unit
def test_gene_prefixed_molecular_profile_surfaces_the_full_evidence_set():
    calls = []
    by_profile = {
        # The joined spelling reaches only a compound profile — 1 plausible item.
        "EGFRvIII": [_evidence_item(773, "EGFR Amplification AND EGFR EGFRVIII")],
        # CIViC's actual profile name holds the rest.
        "EGFR vIII": [
            _evidence_item(i, "EGFR VIII") for i in (772, 848, 971, 1017, 1128, 4500)
        ],
    }
    tool = CIViCTool(_load("civic_search_evidence_items"))
    with patch(
        "tooluniverse.civic_tool.requests.post",
        side_effect=_evidence_transport(by_profile, calls),
    ):
        result = tool.run({"molecular_profile": "EGFRvIII", "limit": 20})

    ids = [n["id"] for n in result["data"]["evidenceItems"]["nodes"]]
    assert {971, 1128, 772}.issubset(set(ids))
    # Nothing found under the caller's own spelling is dropped either.
    assert 773 in ids
    assert len(ids) == len(set(ids)) == 7
    note = result.get("normalization_note", "")
    assert "EGFRvIII" in note and "EGFR vIII" in note
    assert "merged" in note
    # Exactly one extra round-trip, and only because the prefix condition held.
    assert calls == ["EGFRvIII", "EGFR vIII"]


@pytest.mark.unit
def test_separated_molecular_profile_makes_a_single_query():
    calls = []
    by_profile = {"BRAF V600E": [_evidence_item(1409, "BRAF V600E")]}
    tool = CIViCTool(_load("civic_search_evidence_items"))
    with patch(
        "tooluniverse.civic_tool.requests.post",
        side_effect=_evidence_transport(by_profile, calls),
    ):
        result = tool.run({"molecular_profile": "BRAF V600E", "limit": 5})

    assert [n["id"] for n in result["data"]["evidenceItems"]["nodes"]] == [1409]
    assert "normalization_note" not in result
    assert calls == ["BRAF V600E"]
