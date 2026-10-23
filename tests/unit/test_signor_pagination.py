from unittest.mock import Mock

import pytest

from tooluniverse.signor_tool import DATA_COLUMNS, SIGNORTool


def _row(index: int, columns: int = len(DATA_COLUMNS), signor_index: int = 26) -> str:
    values = [""] * columns
    values[0] = f"source-{index}"
    values[4] = f"target-{index}"
    values[signor_index] = f"SIGNOR-{index}"
    values[signor_index + 1] = "0.5"
    return "\t".join(values)


def _response(text: str) -> Mock:
    return Mock(status_code=200, text=text)


@pytest.mark.parametrize(
    ("operation", "arguments", "text"),
    [
        (
            "get_interactions",
            {"entity_id": "P04637"},
            "\n".join(_row(i) for i in range(7)),
        ),
        (
            "get_pathway",
            {"pathway_id": "SIGNOR-AD"},
            "header\n" + "\n".join(_row(i, 32, 30) for i in range(7)),
        ),
        (
            "connect_proteins",
            {"proteins": ["P04637", "Q00987"]},
            "\n".join(_row(i) for i in range(7)),
        ),
    ],
)
def test_signor_truncated_operations_have_recoverable_offsets(
    operation, arguments, text
):
    tool = SIGNORTool({"name": "test", "fields": {"operation": operation}})
    tool.session.get = Mock(return_value=_response(text))

    first = tool.run({**arguments, "limit": 3, "offset": 0})
    second = tool.run({**arguments, "limit": 3, "offset": 3})
    tail = tool.run({**arguments, "limit": 3, "offset": 6})

    assert [r["signor_id"] for r in first["data"]] == [
        "SIGNOR-0",
        "SIGNOR-1",
        "SIGNOR-2",
    ]
    assert [r["signor_id"] for r in second["data"]] == [
        "SIGNOR-3",
        "SIGNOR-4",
        "SIGNOR-5",
    ]
    assert [r["signor_id"] for r in tail["data"]] == ["SIGNOR-6"]
    assert first["metadata"]["total_interactions"] == 7
    assert first["metadata"]["returned"] == 3
    assert first["metadata"]["offset"] == 0
    assert first["metadata"]["has_more"] is True
    assert first["metadata"]["next_offset"] == 3
    assert tail["metadata"]["has_more"] is False
    assert tail["metadata"]["next_offset"] is None


@pytest.mark.parametrize(
    ("bad_params", "message"),
    [
        ({"limit": 0}, "limit"),
        ({"limit": True}, "limit"),
        ({"limit": "3"}, "limit"),
        ({"offset": -1}, "offset"),
        ({"offset": False}, "offset"),
        ({"offset": "3"}, "offset"),
    ],
)
def test_signor_rejects_invalid_pagination_instead_of_silently_clamping(
    bad_params, message
):
    tool = SIGNORTool({"name": "test", "fields": {"operation": "get_interactions"}})
    tool.session.get = Mock(return_value=_response(_row(0)))

    result = tool.run({"entity_id": "P04637", **bad_params})

    assert result["status"] == "error"
    assert message in result["error"]
