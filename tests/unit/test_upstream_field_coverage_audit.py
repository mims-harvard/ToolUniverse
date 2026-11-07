"""The field axis, measured from the call the sweep already makes.

#824 swept the row axis: search and list tools now report `returned`,
`total_results`, `has_more`, `truncated` and `result_set_complete`. The field
axis -- a wrapper selecting a hand-written subset of each record and returning
it as the record -- can be measured statically for the 102 tools carrying a
declared GraphQL query, because the endpoint can be introspected. For the other
2,786 it cannot: nothing in a config says what the upstream offers.

`scripts/audit_upstream_field_coverage.py` measures it from a live call instead,
recording the upstream JSON at the HTTP layer. These tests pin the two
judgements that make its output worth reading, because both were wrong in the
first version:

  * It must compare VALUES, not key names. ComplexPortal answers `ac`,
    `systematicName` and `participants`; the tool returns `complex_id`,
    `systematic_name` and `subunits`. A key-name diff calls all three losses.
  * A field with one value that moved is a transformation, not a loss.
    ComplexPortal's `species` is split into `species` and `taxonomy_id`, so the
    combined upstream string matches nothing in the output and a naive reading
    calls it dropped.

Measured against CPX-1 while this was written: `participants` kept 25 of 188
leaf values, and the subunit records drop `linkedFeatures` -- which region of
each subunit binds which partner -- and `bioRole`. That is the finding this is
built to surface; whether it is a defect is the judgement rule in
devtu-silent-failures, which no threshold replaces.
"""

import importlib.util
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "scripts" / "audit_upstream_field_coverage.py"
SUMMARIZE = ROOT / "scripts" / "summarize_health_sweep.py"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def audit():
    return _load("audit_upstream_field_coverage", AUDIT)


@pytest.fixture(scope="module")
def summarize():
    return _load("summarize_health_sweep", SUMMARIZE)


def test_a_renamed_field_is_not_reported_as_lost(audit):
    """The property the whole design rests on."""
    upstream = {"systematicName": "SMAD2:SMAD4 complex", "ac": "CPX-1"}
    returned = {"systematic_name": "SMAD2:SMAD4 complex", "complex_id": "CPX-1"}

    rows = {r["field"]: r for r in audit.compare(upstream, returned)}

    assert rows["systematicName"]["kept"] == 1
    assert rows["ac"]["kept"] == 1


def test_a_field_whose_values_vanish_is_reported(audit):
    upstream = {"functions": ["transcriptional repressor", "DNA binding"]}
    returned = {"name": "SMAD complex"}

    rows = {r["field"]: r for r in audit.compare(upstream, returned)}

    # A list's elements collapse onto one path, so the field is `functions[]`.
    assert rows["functions[]"]["kept"] == 0
    assert rows["functions[]"]["total"] == 2


def test_list_elements_collapse_onto_one_field_path(audit):
    """Thirty subunits must not become thirty findings."""
    upstream = {
        "participants": [
            {"name": "SMAD2", "bioRole": "unspecified role"},
            {"name": "SMAD4", "bioRole": "unspecified role"},
        ]
    }
    returned = {"subunits": [{"name": "SMAD2"}, {"name": "SMAD4"}]}

    rows = {r["field"]: r for r in audit.compare(upstream, returned)}

    assert set(rows) == {"participants[].name", "participants[].bioRole"}
    assert rows["participants[].name"]["kept"] == 2
    assert rows["participants[].bioRole"]["kept"] == 0


def test_one_character_values_do_not_match_by_accident(audit):
    """A strand of "+" would survive against any output containing a plus."""
    assert audit.leaf_values({"strand": "+"}) == []
    assert audit.leaf_values({"chrom": "17"}) == ["17"]


def test_booleans_and_nulls_are_not_treated_as_values(audit):
    """`true` appears in almost every payload, so it proves nothing."""
    assert audit.leaf_values({"mapped": True, "missing": None}) == []


def test_a_paged_field_is_not_reported_as_dropped(audit):
    """The false positive a ratio threshold produced, and why the rule is zero.

    MediaDive's upstream answers 3,344 media and the tool returns a page of 20.
    Under a ratio the field scored 20/3344 and read as a loss; the field is
    plainly exposed, and the shortfall is the row axis #824 already discloses.
    """
    upstream = {"data": [{"name": f"medium {i}"} for i in range(50)]}
    returned = {"data": [{"name": f"medium {i}"} for i in range(5)]}

    rows = {r["field"]: r for r in audit.compare(upstream, returned)}

    assert rows["data[].name"]["kept"] == 5
    assert rows["data[].name"]["kept"] > 0  # so the zero rule does not flag it


def test_a_single_transformed_value_is_below_the_reporting_floor(audit, monkeypatch):
    """ComplexPortal's `species` is split into species + taxonomy_id.

    Its one combined upstream value matches nothing, and reporting that as a
    loss is the false positive the floor exists to stop.
    """
    rows = audit.compare({"species": "Homo sapiens; 9606"}, {"species": "Homo sapiens"})

    assert rows[0]["total"] == 1  # below the default --min-values of 4


def test_a_selected_field_that_is_null_on_this_page_is_not_a_drop(audit):
    """The third false positive, and the one that cost real triage time.

    MediaDive's wrapper does carry `description` and `reference`. Every medium
    matching 'nutrient agar' is null in both, so neither had a value to
    survive and both scored zero -- 0/68 and 0/36 -- in a list of candidates to
    go and fix. A field whose own name reaches the caller was selected,
    whatever this page happened to hold.
    """
    upstream = {"data": [{"reference": f"ref {i}"} for i in range(8)]}
    returned = {"data": [{"reference": None} for _ in range(3)]}

    rows = {r["field"]: r for r in audit.compare(upstream, returned)}

    assert rows["data[].reference"]["kept"] == 0
    assert rows["data[].reference"]["mapped"] is True


def test_a_field_never_asked_for_is_not_excused_by_the_split(audit):
    """The same split must still report what the wrapper never selected."""
    upstream = {"data": [{"link": f"https://example.org/{i}"} for i in range(8)]}
    returned = {"data": [{"name": "medium"} for _ in range(3)]}

    rows = {r["field"]: r for r in audit.compare(upstream, returned)}

    assert rows["data[].link"]["kept"] == 0
    assert rows["data[].link"]["mapped"] is False


def test_a_surviving_sibling_of_the_same_name_does_not_vouch_for_a_drop(audit):
    """What the key-name signal gets wrong on its own, and the correction.

    GEO's esummary carries `accession` twice: the series' own, which the tool
    returns, and `samples[].accession`, which it dropped. A plain key-name
    match found `accession` in the output and called the sample accessions
    selected -- hiding the one finding worth having. A leaf name that already
    reaches the caller from another path explains the match on its own and
    cannot excuse this path.
    """
    upstream = {
        "accession": "GSE313540",
        "samples": [{"accession": f"GSM{i}"} for i in range(9000, 9008)],
    }
    returned = {"accession": "GSE313540"}

    rows = {r["field"]: r for r in audit.compare(upstream, returned)}

    assert rows["accession"]["kept"] == 1
    assert rows["samples[].accession"]["kept"] == 0
    assert rows["samples[].accession"]["mapped"] is False


def test_a_transformed_value_keeps_its_field_out_of_the_drop_list(audit):
    """Synapse maps `type` through a shortener, so no value matches.

    `org.sagebionetworks.repo.model.FileEntity` becomes `file`. The field is
    there under its own name and nothing else in the output supplies a `type`,
    so it is a transformation rather than a drop.
    """
    upstream = {
        "page": [
            {"type": f"org.sagebionetworks.repo.model.FileEntity{i}"} for i in range(6)
        ]
    }
    returned = {"data": [{"type": "file"} for _ in range(6)]}

    rows = {r["field"]: r for r in audit.compare(upstream, returned)}

    assert rows["page[].type"]["kept"] == 0
    assert rows["page[].type"]["mapped"] is True


def test_a_schema_document_is_not_a_record(audit):
    """The largest single false-positive class after pagination.

    ChEMBL's wrappers fetch `/molecule/CHEMBL25.json` and then
    `/molecule/schema.json`. The second document's leaf values are FIELD
    NAMES, so none of them reach the caller and all 20 ChEMBL tools were
    reported as dropping data. None of them were.
    """
    assert audit.describes_the_api_not_a_record(
        {
            "method": "GET",
            "url": "https://www.ebi.ac.uk/chembl/api/data/molecule/schema.json",
        }
    )
    assert audit.describes_the_api_not_a_record(
        {"method": "OPTIONS", "url": "https://x/y"}
    )
    assert not audit.describes_the_api_not_a_record(
        {
            "method": "GET",
            "url": "https://www.ebi.ac.uk/chembl/api/data/molecule/CHEMBL25.json",
        }
    )


def test_a_value_promoted_to_a_key_still_reached_the_caller(audit):
    """Pivoting a long-format response into a map is not a loss.

    `OmniPath_get_annotation_resource_geneset` turns rows of {label, value}
    into `annotations: {<label>: <value>}`. All 9,755 `label` values reach the
    caller as keys and none as values, which read as the biggest drop in the
    catalogue.
    """
    upstream = {"rows": [{"label": f"annotation {i}"} for i in range(8)]}
    returned = {"annotations": {f"annotation {i}": 1 for i in range(8)}}

    rows = {r["field"]: r for r in audit.compare(upstream, returned)}

    assert rows["rows[].label"]["kept"] == 8


def test_transport_and_search_machinery_are_not_the_record(audit):
    """Reported apart from the candidates, because they are never the answer.

    Alliance answers a `resourceDescriptorPage` per cross-reference holding
    the URL template used to build the link the wrapper already returns, and a
    `supplementalData.distinctFieldValues` holding the search facets. Both
    scored as dropped fields on every Alliance tool.
    """
    for field in [
        "gene.crossReferences[].resourceDescriptorPage.urlTemplate",
        "supplementalData.distinctFieldValues.molecularConsequence[]",
        "data[].links.self",
        "data[].relationships.pipeline.links.related",
        "results[].highlights.symbol[]",
        "results[].subject.createdBy.dateCreated",
        "doTerm.definition",
        "esearchresult.translationstack[].term",
    ]:
        assert not audit.is_record_data(field), field
    for field in [
        "samples[].accession",
        "profiles.rows[].expressionUnit",
        "result[].effective_domain_size",
        "participants[].linkedFeatures[].name",
        "[].references",
    ]:
        assert audit.is_record_data(field), field


def test_a_surrogate_id_beside_a_link_is_not_the_record(audit):
    """SGD answers its own row number for every referenced object.

    `{"id": 823128, "display_name": "CAA84998.1", "link": "/locus/S000000259"}`
    -- the id is the database's row number and the identifier that means
    something is in the link, which is what the wrapper reads. Scoped to this
    shape on purpose: a bare numeric `id` IS the identifier in other APIs, and
    those records carry no link beside it.
    """
    stub = {"rows": [{"id": 823128, "display_name": "X", "link": "/locus/S1"}]}
    assert audit.surrogate_id_paths(stub) == {"rows[].id"}

    # A PubChem-shaped record, where the numeric id is the identifier.
    bare = {"rows": [{"id": 2244, "name": "aspirin"}]}
    assert audit.surrogate_id_paths(bare) == set()


def test_pages_of_one_endpoint_are_one_response(audit):
    """Comparing each page against the merged output reported the same field
    once per page, with a different total each time.

    Every `disease_target_score` tool showed
    `data.disease.associatedTargets.rows[].datasourceScores[].id` five times
    over, and page 1's target symbols scored zero because the output holds a
    later page's rows. Grouped by URL, a value that reached the caller from
    any page counts once.
    """
    page_one = {"rows": [{"symbol": f"GENE{i}"} for i in range(6)]}
    page_two = {"rows": [{"symbol": f"GENE{i}"} for i in range(6, 12)]}
    returned = {"hits": [{"symbol": f"GENE{i}"} for i in range(12)]}

    rows = {r["field"]: r for r in audit.compare([page_one, page_two], returned)}

    assert rows["[].rows[].symbol"]["kept"] == 12
    assert rows["[].rows[].symbol"]["total"] == 12


def test_a_record_count_tells_a_cut_response_from_a_whole_one(audit):
    """The longest list of dicts, which is as crude as it needs to be.

    It exists for one decision: whether the response the caller got holds
    fewer records than the endpoint answered. A single dict in a list is not
    a record set -- one-element lists are how APIs wrap a single object -- so
    two or more are required.
    """
    assert audit.record_count({"payload": [{"a": 1}, {"a": 2}, {"a": 3}]}) == 3
    assert audit.record_count({"results": [{"x": [{"y": 1}, {"y": 2}]}]}) == 2
    assert audit.record_count({"wrapped": [{"only": "one"}]}) == 0
    assert audit.record_count({"scalars": [1, 2, 3]}) == 0

    # The shallowest list of records, not the largest one anywhere. A MaveDB
    # score-set search answers 44 score sets and one of their papers carries
    # 100 authors; reading the author list as the record count made both
    # sides look the same size and the cut invisible.
    nested = {
        "scoreSets": [
            {"urn": f"urn:{i}", "authors": [{"name": str(n)} for n in range(100)]}
            for i in range(44)
        ]
    }
    assert audit.record_count(nested) == 44


def test_a_sparse_field_behind_a_declared_cut_is_not_a_drop(audit, monkeypatch):
    """The last false-positive class the three families turned up.

    DisGeNET's VDA example asks for 20 of 100 associations. `alleles_ref` is
    multi-character on 14 of the 100 -- an indel rather than a SNV -- and all
    14 sat outside the page, so a field the wrapper does carry scored 0/14.
    The mapped-but-unseen signal cannot excuse it either, because the wrapper
    renames it to `reference_allele`.

    The rule is narrow on purpose: it applies only when the response was cut
    (fewer records out than in) AND the field is not on every record. A field
    present on all 100 and absent from the output is still reported, which is
    how `yearInitial` stayed visible on the same response.
    """
    upstream = {
        "payload": [
            {"name": f"row{i}", "rare": "indel" if i > 50 else None}
            for i in range(100)
        ]
    }
    returned = {"rows": [{"label": f"row{i}"} for i in range(20)]}

    captured = {
        "method": "GET",
        "url": "https://example.test/summary",
        "status": 200,
        "body": upstream,
    }
    findings = _run_audit_over(audit, monkeypatch, captured, returned)
    buckets = findings[0]
    assert buckets["thin_fields"] == []
    assert [row["field"] for row in buckets["sparse_behind_a_cut"]] == [
        "payload[].rare"
    ]
    assert buckets["sparse_behind_a_cut"][0]["upstream_records"] == 100
    assert buckets["sparse_behind_a_cut"][0]["returned_records"] == 20


def _run_audit_over(audit, monkeypatch, captured, returned):
    """Drive audit() once with one captured response and one tool result."""

    class FakeUniverse:
        def load_tools(self, include_tools=None):
            return None

        def run(self, call):
            return {"status": "success", "data": returned}

    monkeypatch.setattr(
        audit, "tool_configs", lambda *a, **k: {"T": {"test_examples": [{}]}}
    )
    monkeypatch.setattr(audit, "record_http", lambda: ([captured], lambda: None))
    import sys
    import types

    module = types.ModuleType("tooluniverse")
    module.ToolUniverse = FakeUniverse
    monkeypatch.setitem(sys.modules, "tooluniverse", module)
    return audit.audit(names=["T"], min_values=4)


def test_the_summariser_merges_the_shards_and_records_the_count(summarize, tmp_path):
    """Measured and then thrown away is the failure mode to avoid."""
    shard = tmp_path / "shards" / "a"
    shard.mkdir(parents=True)
    (shard / "FIELD_COVERAGE_0.json").write_text(
        json.dumps(
            [
                {
                    "tool": "ComplexPortal_get_complex",
                    "thin_fields": [
                        {"field": "participants[].bioRole", "kept": 0, "total": 6}
                    ],
                },
                {"tool": "Fine_tool", "thin_fields": []},
                {"tool": "ClinVar_get_submitted_records", "skipped": "no JSON"},
            ]
        )
    )

    parsed = summarize.parse_coverage([str(shard / "FIELD_COVERAGE_*.json")])

    assert parsed["audited"] == 2
    assert parsed["skipped"] == 1
    assert list(parsed["thin"]) == ["ComplexPortal_get_complex"]


def test_the_summary_says_a_thin_field_is_not_a_verdict(summarize):
    """The output is read by whoever triages it, so the caveat ships with it."""
    text, row = summarize.build_summary(
        {"uniprot": True},
        {"uniprot": 10},
        set(),
        set(),
        1,
        coverage={
            "audited": 2,
            "skipped": 1,
            "thin": {"ComplexPortal_get_complex": ["participants[].bioRole 0/6"]},
        },
    )

    assert "## Upstream field coverage" in text
    assert "not a verdict" in text
    assert row["coverage_audited"] == 2
    assert row["coverage_thin_tools"] == 1


def test_the_weekly_workflow_runs_the_audit_and_keeps_its_output():
    """An artifact nothing reads is the same as not measuring."""
    workflow = (ROOT / ".github/workflows/weekly-tool-healthcheck.yml").read_text()

    assert "audit_upstream_field_coverage.py" in workflow
    assert "FIELD_COVERAGE_${{ matrix.shard }}.json" in workflow
    assert "--coverage 'shards/*/FIELD_COVERAGE_*.json'" in workflow
    # The sweep is a canary, not a gate, and so is this.
    assert workflow.count("continue-on-error: true") >= 3
