"""Pagination regressions for DNA_find_orfs."""

import pytest

from tooluniverse.dna_tools import DNATool


pytestmark = pytest.mark.unit


def _tool():
    return DNATool({"name": "DNA_find_orfs", "fields": {"operation": "find_orfs"}})


SEQUENCE_WITH_60_ORFS = ("ATG" + "AAA" * 3 + "TAA") * 60


def test_orf_second_page_is_reachable_and_tail_terminates():
    tool = _tool()
    first = tool.run(
        {
            "sequence": SEQUENCE_WITH_60_ORFS,
            "min_length": 15,
            "strand": "forward",
            "limit": 50,
            "offset": 0,
        }
    )
    tail = tool.run(
        {
            "sequence": SEQUENCE_WITH_60_ORFS,
            "min_length": 15,
            "strand": "forward",
            "limit": 50,
            "offset": 50,
        }
    )

    assert first["data"]["num_orfs_found"] == 60
    assert first["data"]["orfs_returned"] == 50
    assert first["data"]["next_offset"] == 50
    assert tail["data"]["orfs_returned"] == 10
    assert tail["data"]["has_more"] is False
    assert tail["data"]["next_offset"] is None
    assert {row["start"] for row in first["data"]["orfs"]}.isdisjoint(
        {row["start"] for row in tail["data"]["orfs"]}
    )


@pytest.mark.parametrize(
    "arguments, message",
    [
        ({"limit": 0}, "limit"),
        ({"limit": True}, "limit"),
        ({"offset": -1}, "offset"),
        ({"offset": True}, "offset"),
    ],
)
def test_invalid_orf_pagination_is_rejected(arguments, message):
    result = _tool().run(
        {
            "sequence": SEQUENCE_WITH_60_ORFS,
            "min_length": 15,
            "strand": "forward",
            **arguments,
        }
    )
    assert result["status"] == "error"
    assert message in result["error"]
