from unittest.mock import MagicMock

from tooluniverse.nhanes_tool import NHANESTool


def _tool():
    return NHANESTool(
        {"name": "nhanes_search_datasets", "fields": {"endpoint": "search"}}
    )


def _fake_cycle(cycle, components, search_term, datasets, seen_files):
    for index in range(5):
        file_name = f"FILE_{cycle}_{index}"
        if file_name not in seen_files:
            seen_files.add(file_name)
            datasets.append({"file_name": file_name, "cycle": cycle})


def test_search_reports_exact_total_and_adjacent_page():
    tool = _tool()
    tool._search_cycle = MagicMock(side_effect=_fake_cycle)

    result = tool._search_datasets(
        {"search_term": "health", "year": "2017-2018", "limit": 2, "offset": 2}
    )

    data = result["data"]
    assert [row["file_name"] for row in data["datasets"]] == [
        "FILE_2017-2018_2",
        "FILE_2017-2018_3",
    ]
    assert data["count"] == 2
    assert data["total_count"] == 5
    assert data["has_more"] is True
    assert data["next_offset"] == 4
    assert data["result_set_complete"] is False


def test_search_scans_every_documented_default_cycle_before_paginating():
    tool = _tool()
    tool._search_cycle = MagicMock(side_effect=_fake_cycle)

    result = tool._search_datasets({"search_term": "health", "limit": 1})

    assert result["data"]["cycles_searched"] == ["2021-2023", "2017-2018"]
    assert result["data"]["total_count"] == 10
    assert tool._search_cycle.call_count == 2


def test_search_tail_page_terminates_and_invalid_cycle_is_rejected():
    tool = _tool()
    tool._search_cycle = MagicMock(side_effect=_fake_cycle)

    tail = tool._search_datasets(
        {"search_term": "health", "year": "2017-2018", "limit": 2, "offset": 4}
    )
    invalid = tool._search_datasets({"year": "2019-2020"})

    assert tail["data"]["count"] == 1
    assert tail["data"]["has_more"] is False
    assert tail["data"]["next_offset"] is None
    assert invalid["status"] == "error"

