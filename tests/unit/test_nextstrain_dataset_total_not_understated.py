"""Regression tests for Nextstrain_list_datasets truncation reporting.

The listing endpoint caps each pathogen's ``datasets`` array. Previously the
grand total in ``metadata.total_datasets`` was computed from those capped
arrays, so the response confidently reported a catalogue far smaller than the
real one (113 vs. 295 against the live API) with no way to page past the cap.

These tests pin the corrected behaviour: the reported total always equals the
sum of the per-pathogen ``dataset_count`` values, truncation is disclosed at
the top level, and the cap is caller-controllable.
"""

from unittest.mock import patch

import pytest

from tooluniverse.nextstrain_tool import NextstrainTool


LIST_CONFIG = {
    "name": "Nextstrain_list_datasets",
    "type": "NextstrainTool",
    "fields": {"endpoint_type": "list_datasets"},
}

GET_CONFIG = {
    "name": "Nextstrain_get_dataset",
    "type": "NextstrainTool",
    "fields": {"endpoint_type": "get_dataset"},
}


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _available_payload():
    """25 avian-flu datasets, 12 ncov, 3 zika -> 40 across 3 pathogens."""
    requests_list = []
    requests_list += [f"avian-flu/build-{i:02d}" for i in range(25)]
    requests_list += [f"ncov/build-{i:02d}" for i in range(12)]
    requests_list += [f"zika/build-{i:02d}" for i in range(3)]
    return {"datasets": [{"request": r} for r in requests_list]}


@pytest.fixture
def list_tool():
    return NextstrainTool(LIST_CONFIG)


def _run_list(tool, arguments):
    with patch(
        "tooluniverse.nextstrain_tool.requests.get",
        return_value=_FakeResponse(_available_payload()),
    ):
        return tool.run(arguments)


def test_total_datasets_matches_sum_of_per_pathogen_counts(list_tool):
    result = _run_list(list_tool, {})

    assert result["status"] == "success"
    expected_total = sum(entry["dataset_count"] for entry in result["data"])
    assert expected_total == 40
    assert result["metadata"]["total_datasets"] == expected_total

    # The total must NOT be the sum of the truncated listings.
    listed = sum(len(entry["datasets"]) for entry in result["data"])
    assert listed == 10 + 10 + 3  # capped at the 10-per-pathogen default
    assert listed < expected_total
    assert result["metadata"]["total_datasets"] != listed


def test_truncation_is_disclosed_at_top_level(list_tool):
    result = _run_list(list_tool, {})

    assert result["truncated"] is True
    note = result["truncation_note"]
    assert "295" not in note  # note is derived from the payload, not hardcoded
    assert "40" in note  # true total is named
    assert "datasets_per_pathogen" in note  # tells the caller how to get the rest
    assert result["metadata"]["truncated"] is True
    assert result["metadata"]["listed_datasets"] == 23


def test_truncated_pathogen_entries_are_flagged(list_tool):
    result = _run_list(list_tool, {})
    by_pathogen = {entry["pathogen"]: entry for entry in result["data"]}

    assert by_pathogen["avian-flu"]["datasets_truncated"] is True
    assert by_pathogen["avian-flu"]["datasets_listed"] == 10
    assert by_pathogen["avian-flu"]["dataset_count"] == 25

    # A pathogen that fits under the cap is not flagged.
    assert "datasets_truncated" not in by_pathogen["zika"]
    assert by_pathogen["zika"]["datasets_listed"] == 3


def test_datasets_per_pathogen_zero_returns_everything(list_tool):
    result = _run_list(list_tool, {"datasets_per_pathogen": 0})

    listed = sum(len(entry["datasets"]) for entry in result["data"])
    assert listed == 40
    assert result["metadata"]["total_datasets"] == 40
    assert result["metadata"]["listed_datasets"] == 40
    assert result["truncated"] is False
    assert "truncation_note" not in result
    assert all("datasets_truncated" not in e for e in result["data"])


def test_datasets_per_pathogen_raises_the_cap(list_tool):
    result = _run_list(list_tool, {"datasets_per_pathogen": 12})

    by_pathogen = {entry["pathogen"]: entry for entry in result["data"]}
    assert by_pathogen["avian-flu"]["datasets_listed"] == 12
    assert by_pathogen["ncov"]["datasets_listed"] == 12
    assert "datasets_truncated" not in by_pathogen["ncov"]
    # avian-flu (25) is still cut, so truncation stays disclosed.
    assert result["truncated"] is True
    assert result["metadata"]["total_datasets"] == 40


def test_pathogen_filter_totals_reflect_only_the_filtered_pathogen(list_tool):
    result = _run_list(list_tool, {"pathogen": "ncov", "datasets_per_pathogen": 0})

    assert result["metadata"]["total_pathogens"] == 1
    assert result["metadata"]["total_datasets"] == 12
    assert result["truncated"] is False


def test_negative_datasets_per_pathogen_is_rejected(list_tool):
    result = _run_list(list_tool, {"datasets_per_pathogen": -5})
    assert result["status"] == "error"
    assert "datasets_per_pathogen" in result["error"]


def test_get_dataset_returns_all_colorings():
    payload = {
        "meta": {
            "title": "Test build",
            "colorings": [{"key": f"color_{i}"} for i in range(20)],
        },
        "tree": {"children": [{"name": "a"}, {"name": "b"}]},
    }
    tool = NextstrainTool(GET_CONFIG)
    with patch(
        "tooluniverse.nextstrain_tool.requests.get",
        return_value=_FakeResponse(payload),
    ):
        result = tool.run({"dataset": "zika"})

    assert result["status"] == "success"
    data = result["data"]
    # Previously capped at 15, silently dropping the remaining keys.
    assert len(data["available_colorings"]) == 20
    assert data["available_colorings_count"] == 20
    assert data["num_sequences"] == 2
