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
