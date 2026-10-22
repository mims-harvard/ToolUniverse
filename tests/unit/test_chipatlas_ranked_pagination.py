from unittest.mock import Mock, patch

import pytest

from tooluniverse.chipatlas_tool import ChIPAtlasTool


@pytest.mark.parametrize(
    ("operation", "arguments", "text", "key", "value_key"),
    [
        (
            "get_colocalization",
            {"antigen": "CTCF", "cell_type_class": "Blood"},
            "header\n" + "\n".join(f"EXP{i}\tBlood\tP{i}\t{100-i}" for i in range(7)),
            "partners",
            "protein",
        ),
        (
            "get_target_genes",
            {"antigen": "GATA1", "distance": "5"},
            "header\n" + "\n".join(f"G{i}\t{100-i}" for i in range(7)),
            "target_genes",
            "gene",
        ),
    ],
)
def test_chipatlas_ranked_results_are_recoverable(
    operation, arguments, text, key, value_key
):
    response = Mock(status_code=200, text=text)
    response.raise_for_status.return_value = None
    tool = ChIPAtlasTool({"name": "test", "fields": {"operation": operation}})

    with patch("tooluniverse.chipatlas_tool.requests.get", return_value=response):
        first = tool.run({"operation": operation, **arguments, "limit": 3, "offset": 0})["data"]
        second = tool.run({"operation": operation, **arguments, "limit": 3, "offset": 3})["data"]
        tail = tool.run({"operation": operation, **arguments, "limit": 3, "offset": 6})["data"]

    prefix = "P" if operation == "get_colocalization" else "G"
    assert [r[value_key] for r in first[key]] == [f"{prefix}{i}" for i in range(3)]
    assert [r[value_key] for r in second[key]] == [f"{prefix}{i}" for i in range(3, 6)]
    assert [r[value_key] for r in tail[key]] == [f"{prefix}6"]
    assert first["next_offset"] == 3
    assert first["has_more"] is True
    assert tail["next_offset"] is None
    assert tail["has_more"] is False
