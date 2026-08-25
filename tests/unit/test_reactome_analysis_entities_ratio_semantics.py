"""Regression guard for Fix-R37: ReactomeAnalysisTool emitted Reactome's raw
`entities.ratio` as `entities_ratio` directly beneath `entities_found` and
`entities_total`, which states by name and by adjacency that it is found/total
-- the pathway coverage a reader of an enrichment result wants.

It is not: `ratio` is the pathway's share of Reactome's entity universe for its
species, so it depends only on pathway SIZE and is identical for any submitted
gene list. Ranking by it ranks pathways by size, not by enrichment, and the
error runs in both directions (small pathways understate, large overstate).

The tool now emits `entities_coverage` (= found/total) next to the counts and
exposes the raw value under the self-describing name
`pathway_size_fraction_of_reactome`, with `entities_ratio` kept as a deprecated
alias. No numeric value reported by Reactome was changed. The canonical
explanation lives in the field descriptions in reactome_analysis_tools.json.
"""

import json
from importlib import resources
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.reactome_analysis_tool import ReactomeAnalysisTool

pytestmark = pytest.mark.unit

# Synthetic universe size for the fixture below. The live divisor is per-species
# and drifts between Reactome releases, which is exactly why the tool never
# hard-codes one.
HUMAN_ENTITY_UNIVERSE = 16251

# Values copied verbatim from a live enrichment run so the test pins real
# Reactome semantics rather than invented arithmetic.
LIVE_PATHWAYS = [
    ("R-HSA-6796648", "TP53 Regulates Transcription of DNA Repair Genes", 7, 86),
    ("R-HSA-3700989", "Transcriptional Regulation by TP53", 9, 487),
    ("R-HSA-212436", "Generic Transcription Pathway", 9, 1574),
    ("R-HSA-73857", "RNA Polymerase II Transcription", 9, 1678),
]


def _tool(name="ReactomeAnalysis_pathway_enrichment", endpoint="pathway_enrichment"):
    return ReactomeAnalysisTool({"name": name, "fields": {"endpoint": endpoint}})


def _payload():
    """Reactome's own response shape, with `ratio` derived exactly the way the
    live service derives it: pathway size over the species entity universe."""
    return {
        "summary": {"token": "TOKEN123", "type": "OVERREPRESENTATION"},
        "pathwaysFound": len(LIVE_PATHWAYS),
        "identifiersNotFound": 0,
        "pathways": [
            {
                "stId": st_id,
                "name": name,
                "species": {"name": "Homo sapiens"},
                "llp": True,
                "inDisease": False,
                "entities": {
                    "total": total,
                    "found": found,
                    "ratio": total / HUMAN_ENTITY_UNIVERSE,
                    "pValue": 1e-9,
                    "fdr": 1e-7,
                },
                "reactions": {"total": 17, "found": 15},
            }
            for st_id, name, found, total in LIVE_PATHWAYS
        ],
    }


def _run(payload, tool=None, identifiers="TP53,BRCA1,BRCA2,ATM,CHEK2"):
    tool = tool or _tool()
    resp = MagicMock()
    resp.json.return_value = payload
    with patch(
        "tooluniverse.reactome_analysis_tool.requests.post", return_value=resp
    ) as post:
        result = tool.run({"identifiers": identifiers})
    assert post.called, "unit test must not reach the network"
    return result


def test_coverage_is_found_over_total():
    pathways = _run(_payload())["data"]["pathways"]

    assert len(pathways) == len(LIVE_PATHWAYS)
    for pw, (_, _, found, total) in zip(pathways, LIVE_PATHWAYS):
        assert pw["entities_found"] == found
        assert pw["entities_total"] == total
        assert pw["entities_coverage"] == pytest.approx(found / total)


def test_size_fraction_is_reactomes_ratio_and_not_coverage():
    pathways = _run(_payload())["data"]["pathways"]

    for pw, (_, _, _, total) in zip(pathways, LIVE_PATHWAYS):
        raw = pw["pathway_size_fraction_of_reactome"]
        # Reactome's number is passed through untouched, and its divisor is the
        # same universe size for every pathway -- which is exactly why it says
        # nothing about the submitted identifiers.
        assert raw == pytest.approx(total / HUMAN_ENTITY_UNIVERSE)
        # It must never be confused with coverage.
        assert raw != pytest.approx(pw["entities_coverage"])


def test_deprecated_entities_ratio_alias_is_kept_but_is_not_coverage():
    pathways = _run(_payload())["data"]["pathways"]

    for pw in pathways:
        assert pw["entities_ratio"] == pw["pathway_size_fraction_of_reactome"]
        assert pw["entities_ratio"] != pytest.approx(pw["entities_coverage"])


def test_misreading_ratio_as_coverage_errs_in_both_directions():
    """Small pathways understate, large pathways overstate -- so the defect is
    not a one-directional bias that a reader could mentally correct for."""
    by_name = {pw["name"]: pw for pw in _run(_payload())["data"]["pathways"]}

    small = by_name["TP53 Regulates Transcription of DNA Repair Genes"]
    large = by_name["Generic Transcription Pathway"]

    assert small["entities_ratio"] < small["entities_coverage"]
    assert large["entities_ratio"] > large["entities_coverage"]


def test_ranking_by_size_fraction_disagrees_with_ranking_by_coverage():
    pathways = _run(_payload())["data"]["pathways"]

    by_size = [p["name"] for p in sorted(pathways, key=lambda p: -p["entities_ratio"])]
    by_coverage = [
        p["name"] for p in sorted(pathways, key=lambda p: -p["entities_coverage"])
    ]
    assert by_size != by_coverage
    # Ranking by the raw ratio is exactly a ranking by pathway size.
    by_total = [p["name"] for p in sorted(pathways, key=lambda p: -p["entities_total"])]
    assert by_size == by_total


@pytest.mark.parametrize(
    "mutate, expected_total",
    [
        (lambda e: e.update({"total": 0, "found": 0, "ratio": 0.0}), 0),
        (lambda e: e.pop("total"), None),
    ],
    ids=["zero_total", "missing_total"],
)
def test_unusable_counts_yield_null_coverage_without_raising(mutate, expected_total):
    payload = _payload()
    mutate(payload["pathways"][0]["entities"])

    pw = _run(payload)["data"]["pathways"][0]
    assert pw["entities_total"] == expected_total
    assert pw["entities_coverage"] is None


def test_expression_analysis_carries_the_same_documented_fields():
    payload = _payload()
    payload["summary"]["type"] = "EXPRESSION"
    payload["expression"] = {"columnNames": ["col1"], "min": -1.8, "max": 3.1}
    for pw in payload["pathways"]:
        pw["entities"]["exp"] = [2.5]

    tool = _tool("ReactomeAnalysis_expression_analysis", "expression_analysis")
    result = _run(payload, tool, identifiers="PTEN\t2.5")

    pw = result["data"]["pathways"][0]
    assert pw["entities_coverage"] == pytest.approx(7 / 86)
    assert pw["pathway_size_fraction_of_reactome"] == pw["entities_ratio"]
    assert pw["entities_exp"] == [2.5]


def test_every_formatter_backed_tool_documents_the_fields_it_emits():
    """The five pathway-returning tools share one formatter, so a schema that
    lags behind it re-creates exactly the misreading this fix removes. Nothing
    else catches the drift: return_schema validation never sets
    additionalProperties=false, so undeclared keys pass silently."""
    emitted = set(_run(_payload())["data"]["pathways"][0])

    config = json.loads(
        resources.files("tooluniverse.data")
        .joinpath("reactome_analysis_tools.json")
        .read_text()
    )
    formatter_backed = {
        "pathway_enrichment",
        "species_comparison",
        "token_result",
        "expression_analysis",
        "species_comparison_v2",
    }

    checked = 0
    for tool in config:
        if tool["fields"]["endpoint"] not in formatter_backed:
            continue
        checked += 1
        schema = tool["return_schema"]["oneOf"][0]["properties"]["pathways"]
        declared = set(schema.get("items", {}).get("properties", {}))
        for key in ("entities_coverage", "pathway_size_fraction_of_reactome"):
            assert key in declared, (
                f"{tool['name']} emits {key} but does not declare it"
            )
        undocumented = emitted - declared - {"entities_exp"}
        assert not undocumented, f"{tool['name']} emits undeclared keys: {undocumented}"

    assert checked == len(formatter_backed)
