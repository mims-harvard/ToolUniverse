"""CIViC's evidence/assertion join, the variant's annotation, the disease counts.

arXiv 2609.26836 reports three CIViC gaps. Measured live 2026-11-12 and
2026-11-13, against GraphQL introspection of the live schema:

- `civic_get_assertion` returned `evidenceItemsCount: 3` and no items, and
  nothing else in the catalogue could fetch them -- `civic_search_evidence_items`
  has no assertion filter. The count named evidence that could not be reached.
  The reverse link was missing too: `EvidenceItem.assertions` exists upstream
  and `civic_get_evidence_item` did not ask for it, so the hierarchy was
  severed in both directions.
- `civic_get_variant` asked for 12 of GeneVariant's 32 fields. `myVariantInfo`
  (62 annotation fields: gnomAD frequencies, every pathogenicity predictor with
  score and call, conservation, dbSNP/COSMIC/ClinVar cross-references) was
  absent, as were `deprecated`, `deprecationReason` and `flagged` -- a retired
  or flagged variant came back indistinguishable from a current one.
- `civic_search_diseases` returned `{id, name}` of BrowseDisease's 13 fields.
  'Melanoma' matches nine CIViC diseases whose evidence ranges from 304 items
  to 1, and the tool returned nine ids and nine names with nothing to choose
  between them. `evidenceItemCount`, `assertionCount`, `variantCount`, `doid`
  and `diseaseAliases` were all available and none was asked for. The schema
  additionally asserted that the connection "reports no filter-aware total";
  `filteredCount` is exactly that and it is there.

And the paper's fourth CIViC claim, that a parent-disease search misses
subtype evidence, is backwards: `disease="Melanoma"` returns 235 items drawn
from SEVEN diseases, because the filter is a name substring that silently
unions them. 235 is neither Melanoma's own 304 nor any ontology subtree.
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

CONFIG = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "tooluniverse"
    / "data"
    / "civic_tools.json"
)
TOOLS = {t["name"]: t for t in json.loads(CONFIG.read_text())}
SOURCE = (
    Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "civic_tool.py"
).read_text()


def _query(name):
    return TOOLS[name]["fields"]["query"]


def test_an_assertion_carries_the_evidence_it_is_made_from():
    query = _query("civic_get_assertion")
    assert "evidenceItemsCount" in query
    assert "evidenceItems {" in query
    # The item must be usable on arrival, not just an id: its own level, its
    # status (an assertion can cite an item that was later REJECTED), and the
    # source it rests on.
    items = query.split("evidenceItems {", 1)[1]
    for field in (
        "evidenceLevel",
        "evidenceType",
        "status",
        "source {",
        "evidenceRating",
    ):
        assert field in items, field


def test_an_evidence_item_carries_the_assertions_that_cite_it():
    query = _query("civic_get_evidence_item")
    assert "assertions {" in query
    block = query.split("assertions {", 1)[1]
    for field in ("status", "assertionType", "ampLevel"):
        assert field in block, field


def test_the_evidence_item_query_does_not_ask_for_variantHgvs():
    # Measured 2026-11-13: upstream declares EvidenceItem.variantHgvs
    # non-nullable and returns null for it, so asking for the field fails the
    # WHOLE query ("Cannot return null for non-nullable field
    # EvidenceItem.variantHgvs") and the tool returns nothing at all.
    assert "variantHgvs" not in _query("civic_get_evidence_item")


def test_a_variant_carries_its_annotation_and_its_retirement():
    query = _query("civic_get_variant")
    for field in ("deprecated", "deprecationReason", "flagged", "myVariantInfo {"):
        assert field in query, field
    mvi = query.split("myVariantInfo {", 1)[1]
    # A predictor's call without its score cannot be weighed, so both are asked
    # for; the frequencies and cross-references are the other half.
    for field in (
        "siftPrediction",
        "siftScore",
        "polyphen2HvarPrediction",
        "polyphen2HvarScore",
        "revelScore",
        "caddPhred",
        "gnomadExomeAlleleFrequency",
        "gnomadGenomeAlleleFrequency",
        "dbsnpRsid",
        "cosmicId",
        "clinvarId",
        "clinvarClinicalSignificance",
        "gerp",
        "phyloP100way",
    ):
        assert field in mvi, field


def test_a_disease_row_says_how_much_evidence_it_has():
    query = _query("civic_search_diseases")
    for field in (
        "evidenceItemCount",
        "assertionCount",
        "variantCount",
        "featureCount",
        "doid",
        "diseaseAliases",
        "deprecated",
        "filteredCount",
        "totalCount",
    ):
        assert field in query, field

    props = TOOLS["civic_search_diseases"]["return_schema"]["properties"]["data"][
        "properties"
    ]["browseDiseases"]["properties"]
    assert "filteredCount" in props
    # The old schema asserted the opposite of what the connection does, on
    # pageInfo and on hasNextPage.
    assert "no filter-aware total" not in props["pageInfo"]["description"]
    assert (
        "no filter-aware total"
        not in props["pageInfo"]["properties"]["hasNextPage"]["description"]
    )
    node = props["nodes"]["items"]["properties"]
    assert "evidenceItemCount" in node


def test_the_disease_filter_discloses_that_it_unions_diseases():
    # The handler tallies the diseases present in the page it returns.
    assert '"disease_filter"' in SOURCE or "disease_filter" in SOURCE
    block = SOURCE.split('tool_name == "civic_search_evidence_items"', 1)[1]
    assert "diseases_on_this_page" in block
    assert "substring" in block
    description = TOOLS["civic_search_evidence_items"]["parameter"]["properties"][
        "disease"
    ]["description"]
    assert "SUBSTRING" in description.upper()
    assert "union" in description.lower()
