"""A page of FAERS case reports must say how big the matching set is.

The six ``FAERS_search_*`` detail tools returned openFDA's page of case reports
as a bare list and threw away ``meta.results.total`` from the very response body
they were already parsing, so a page and a complete answer were indistinguishable.
``faers_detail_envelope`` in ``src/tooluniverse/openfda_adv_tool.py`` records the
live measurements; the sharpest is 10 reports returned against 5941 matching.

This is a return-shape change (array -> object), taken deliberately because
there is nowhere on a list to put a total. The sibling
``OpenFDA_search_drug_approvals`` already returns an object with a total, and the
key names are the repo-wide ``count``/``total_available``/``truncated``/
``truncation_note`` vocabulary rather than a sixth spelling of it.

Network-free: the envelope helper is exercised directly.
"""

import json
from pathlib import Path

import pytest

import tooluniverse
from tooluniverse.openfda_adv_tool import faers_detail_envelope

pytestmark = pytest.mark.unit

DATA_DIR = Path(tooluniverse.__file__).parent / "data"
TOOLS_DIR = Path(tooluniverse.__file__).parent / "tools"
DETAIL_TOOLS = [
    "FAERS_search_adverse_event_reports",
    "FAERS_search_reports_by_drug_and_reaction",
    "FAERS_search_serious_reports_by_drug",
    "FAERS_search_reports_by_drug_and_indication",
    "FAERS_search_reports_by_drug_and_outcome",
    "FAERS_search_reports_by_drug_combination",
]


def _config(tool_name):
    configs = json.loads(
        (DATA_DIR / "fda_drug_adverse_event_detail_tools.json").read_text()
    )
    return next(config for config in configs if config["name"] == tool_name)


def test_a_truncated_page_names_the_total_it_was_cut_from():
    envelope = faers_detail_envelope([{"safetyreportid": "1"}] * 10, 5941, 10, 0)

    assert envelope["count"] == 10
    assert envelope["total_available"] == 5941
    assert envelope["truncated"] is True
    assert "5941" in envelope["truncation_note"]


def test_the_last_page_is_not_reported_as_truncated():
    """skip + count == total is the complete answer, not a partial one."""
    envelope = faers_detail_envelope([{"safetyreportid": "1"}], 5941, 5, 5940)

    assert envelope["truncated"] is False
    assert "truncation_note" not in envelope


def test_no_matches_reports_a_total_of_zero_not_a_missing_total():
    envelope = faers_detail_envelope([], 0, 5, 0)

    assert envelope["total_available"] == 0
    assert envelope["truncated"] is False


def test_a_missing_upstream_total_stays_none_rather_than_becoming_zero():
    """None means "openFDA did not say"; 0 would assert an absence."""
    envelope = faers_detail_envelope([{"safetyreportid": "1"}], None, 10, 0)

    assert envelope["total_available"] is None
    assert envelope["truncated"] is False
    assert "truncation_note" not in envelope


@pytest.mark.parametrize("tool_name", DETAIL_TOOLS)
def test_the_return_schema_describes_the_envelope_not_a_list(tool_name):
    return_schema = _config(tool_name)["return_schema"]

    assert return_schema["type"] == "object"
    assert return_schema["properties"]["reports"]["type"] == "array"
    assert return_schema["properties"]["total_available"]["type"] == ["integer", "null"]
    assert "total_available" in return_schema["required"]


@pytest.mark.parametrize("tool_name", DETAIL_TOOLS)
def test_the_description_warns_that_count_is_not_the_match_count(tool_name):
    description = _config(tool_name)["description"]

    assert "total_available" in description
    assert "5941" in description


@pytest.mark.parametrize("tool_name", DETAIL_TOOLS)
def test_the_generated_wrapper_annotates_the_new_return_type(tool_name):
    """`src/tooluniverse/tools/*.py` is generated but tracked, and it ships.

    A config-only change would leave every Python-API caller with a signature
    promising `list[Any]` for something that is now a dict.
    """
    source = (TOOLS_DIR / f"{tool_name}.py").read_text()

    assert ") -> dict[str, Any]:" in source
    assert "list[Any]" not in source


def test_the_seriousness_return_schema_still_documents_the_serious_mix():
    """Pinned by test_faers_serious_reports_seriousness_filter; keep it true."""
    description = _config("FAERS_search_serious_reports_by_drug")["return_schema"][
        "description"
    ]

    assert "serious" in description
    assert "non-serious" in description
