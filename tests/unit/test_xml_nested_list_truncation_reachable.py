"""XMLTool nested list fields must disclose truncation and stay reachable.

Regression for Fix-R28B. `_NESTED_LIST_DISPLAY_CAP = 25` bounds the payload of a
nested list field, but the cut was made in raw document order with no flag, no
count on the untruncated path, no ranking and no way to page. Reproduced live
against the real DrugBank dataset before the fix:

    drugbank_get_drug_interactions_by_drug_name_or_id
        {"query": "labetalol", "exact_match": true, "limit": 100}
    -> interacting_drugs_total_count 1855, 25 entries returned, 'nifedipine'
       absent (it sits at index 71), and the reverse nifedipine query likewise
       omitted labetalol.

Clinically that reads as "labetalol and nifedipine do not interact", when
DrugBank in fact documents "The risk or severity of congestive heart failure and
hypotension can be increased when Nifedipine is combined with Labetalol."

The fix is additive and does NOT change the shared cap value: disclosure keys
are emitted next to every nested list, and the optional `nested_contains` /
`nested_offset` arguments default to the previous behaviour.

The real DrugBank dataset is a large HF download CI does not have, so these
tests drive XMLDatasetTool against a small synthetic XML file via the
`local_dataset_path` setting -- no network.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import tooluniverse  # noqa: E402

pytestmark = pytest.mark.unit

DATA_DIR = Path(tooluniverse.__file__).parent / "data"
NS = "http://www.drugbank.ca"

# 80 interaction partners, with the clinically interesting one deliberately
# parked at index 71 -- exactly where Nifedipine sits in labetalol's real
# record, i.e. well past the 25-entry display cap.
PARTNERS = [(f"DB{i:05d}", f"Filler{i}", f"Filler{i} interacts.") for i in range(80)]
PARTNERS[71] = (
    "DB01115",
    "Nifedipine",
    "The risk or severity of congestive heart failure and hypotension can be "
    "increased when Nifedipine is combined with Labetalol.",
)


def _write_dataset(tmp_path):
    interactions = "".join(
        f"<drug-interaction><drugbank-id>{i}</drugbank-id>"
        f"<name>{n}</name><description>{d}</description></drug-interaction>"
        for i, n, d in PARTNERS
    )
    xml = (
        f'<drugbank xmlns="{NS}">'
        f'<drug><drugbank-id primary="true">DB00598</drugbank-id>'
        f"<name>Labetalol</name>"
        f"<drug-interactions>{interactions}</drug-interactions>"
        f"<products><product><name>Trandate</name></product></products>"
        f"</drug>"
        f'<drug><drugbank-id primary="true">DB00316</drugbank-id>'
        f"<name>Acetaminophen</name>"
        f"<drug-interactions>"
        f"<drug-interaction><drugbank-id>DB00001</drugbank-id>"
        f"<name>Lepirudin</name><description>Minor.</description>"
        f"</drug-interaction></drug-interactions>"
        f"<products><product><name>Tylenol</name></product></products>"
        f"</drug>"
        f"</drugbank>"
    )
    path = tmp_path / "drugbank_sample.xml"
    path.write_text(xml, encoding="utf-8")
    return str(path)


def _make_tool(tmp_path):
    from tooluniverse.xml_tool import XMLDatasetTool

    config = {
        "name": "drugbank_get_drug_interactions_by_drug_name_or_id",
        "parameter": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "exact_match": {"type": "boolean", "default": False},
                "limit": {"type": "integer", "default": 10},
                "nested_contains": {"type": "string"},
                "nested_offset": {"type": "integer", "default": 0},
            },
            "required": ["query"],
        },
        "settings": {
            "local_dataset_path": _write_dataset(tmp_path),
            "record_xpath": "db:drug",
            "namespaces": {"db": NS},
            "search_fields": ["drug_name", "drugbank_id", "brand_names"],
            "field_mappings": {
                "drug_name": "db:name",
                "drugbank_id": "db:drugbank-id[@primary='true']",
                "interacting_drugs": {
                    "parent_path": "db:drug-interactions/db:drug-interaction",
                    "subfields": {
                        "id": "db:drugbank-id",
                        "name": "db:name",
                        "description": "db:description",
                    },
                },
                "brand_names": "db:products/db:product/db:name",
            },
        },
    }
    tool = XMLDatasetTool(config)
    assert tool.records, "synthetic dataset failed to load"
    return tool


def _labetalol(result):
    records = [r for r in result["data"]["results"] if r["drug_name"] == "Labetalol"]
    assert len(records) == 1
    return records[0]


def test_default_view_is_unchanged_but_now_flags_the_truncation(tmp_path):
    tool = _make_tool(tmp_path)
    record = _labetalol(tool.run({"query": "labetalol", "exact_match": True}))

    # Payload size is unchanged -- the shared cap was NOT raised.
    assert len(record["interacting_drugs"]) == 25
    assert record["interacting_drugs"][0]["name"] == "Filler0"

    assert record["interacting_drugs_total_count"] == 80
    assert record["interacting_drugs_shown_count"] == 25
    assert record["interacting_drugs_offset"] == 0
    assert record["interacting_drugs_truncated"] is True


def test_complete_short_list_is_flagged_as_not_truncated(tmp_path):
    """A complete list and a cut list must not look identical."""
    tool = _make_tool(tmp_path)
    result = tool.run({"query": "acetaminophen", "exact_match": True})
    record = result["data"]["results"][0]

    assert len(record["interacting_drugs"]) == 1
    assert record["interacting_drugs_total_count"] == 1
    assert record["interacting_drugs_shown_count"] == 1
    assert record["interacting_drugs_truncated"] is False


def test_partner_beyond_the_cap_is_reachable_via_nested_contains(tmp_path):
    """The clinical question: is labetalol + nifedipine documented?"""
    tool = _make_tool(tmp_path)
    record = _labetalol(
        tool.run(
            {"query": "labetalol", "exact_match": True, "nested_contains": "nifedipine"}
        )
    )

    assert [e["name"] for e in record["interacting_drugs"]] == ["Nifedipine"]
    assert record["interacting_drugs"][0]["description"].startswith(
        "The risk or severity of congestive heart failure and hypotension"
    )
    assert record["interacting_drugs_total_count"] == 80
    assert record["interacting_drugs_matching_count"] == 1
    assert record["interacting_drugs_truncated"] is False


def test_nested_contains_reports_zero_matches_for_a_genuine_non_interaction(tmp_path):
    """Absence must be reported as a searched-and-found-nothing zero."""
    tool = _make_tool(tmp_path)
    record = _labetalol(
        tool.run(
            {"query": "labetalol", "exact_match": True, "nested_contains": "warfarin"}
        )
    )

    assert record["interacting_drugs"] == []
    assert record["interacting_drugs_matching_count"] == 0
    assert record["interacting_drugs_total_count"] == 80
    assert record["interacting_drugs_truncated"] is False


def test_nested_offset_pages_through_the_full_list(tmp_path):
    tool = _make_tool(tmp_path)
    page = _labetalol(
        tool.run({"query": "labetalol", "exact_match": True, "nested_offset": 50})
    )

    names = [e["name"] for e in page["interacting_drugs"]]
    assert len(names) == 25
    assert "Nifedipine" in names
    assert 50 + names.index("Nifedipine") == 71
    assert page["interacting_drugs_offset"] == 50
    assert page["interacting_drugs_truncated"] is True
    # No filter was applied, so no matching-count is claimed.
    assert "interacting_drugs_matching_count" not in page

    # The last page reports that nothing remains beyond it.
    tail = _labetalol(
        tool.run({"query": "labetalol", "exact_match": True, "nested_offset": 75})
    )
    assert tail["interacting_drugs_shown_count"] == 5
    assert tail["interacting_drugs_truncated"] is False


def test_nested_contains_is_case_insensitive_and_searches_descriptions(tmp_path):
    tool = _make_tool(tmp_path)

    by_name = _labetalol(
        tool.run(
            {"query": "labetalol", "exact_match": True, "nested_contains": "NIFEDIPINE"}
        )
    )
    assert by_name["interacting_drugs_matching_count"] == 1

    by_id = _labetalol(
        tool.run(
            {"query": "labetalol", "exact_match": True, "nested_contains": "DB01115"}
        )
    )
    assert by_id["interacting_drugs_matching_count"] == 1

    by_desc = _labetalol(
        tool.run(
            {
                "query": "labetalol",
                "exact_match": True,
                "nested_contains": "congestive heart failure",
            }
        )
    )
    assert by_desc["interacting_drugs_matching_count"] == 1


def test_search_parameters_echo_the_nested_view(tmp_path):
    tool = _make_tool(tmp_path)
    params = tool.run(
        {
            "query": "labetalol",
            "exact_match": True,
            "nested_contains": "nifedipine",
            "nested_offset": 0,
        }
    )["data"]["search_parameters"]

    assert params["nested_contains"] == "nifedipine"
    assert params["nested_offset"] == 0


def test_shared_display_cap_value_is_not_raised():
    """Other tools share this constant; disclosure was added around it."""
    from tooluniverse.xml_tool import XMLDatasetTool

    assert XMLDatasetTool._NESTED_LIST_DISPLAY_CAP == 25


def test_config_declares_the_optional_parameters_with_inert_defaults():
    configs = json.loads((DATA_DIR / "xml_tools.json").read_text())
    cfg = next(
        c
        for c in configs
        if c["name"] == "drugbank_get_drug_interactions_by_drug_name_or_id"
    )
    props = cfg["parameter"]["properties"]

    assert "nested_contains" in props
    assert props["nested_offset"]["default"] == 0
    # Optional: adding them must not change what callers are required to send.
    assert cfg["parameter"]["required"] == ["query"]

    returned = cfg["return_schema"]["properties"]["results"]["items"]["properties"]
    assert returned["interacting_drugs_total_count"]["type"] == "integer"
    assert returned["interacting_drugs_truncated"]["type"] == "boolean"
