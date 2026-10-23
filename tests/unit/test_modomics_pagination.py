from unittest.mock import Mock, patch

import pytest

from tooluniverse.modomics_tool import MODOMICSTool


@pytest.fixture
def catalog():
    return {
        str(i): {
            "id": i,
            "name": f"methyl modification {i}",
            "short_name": f"m{i}",
            "formula": f"C{i}",
            "reference_moiety": [],
        }
        for i in range(7)
    }


@pytest.mark.parametrize(
    ("endpoint", "base_arguments", "key"),
    [
        ("list_modifications", {}, "modifications"),
        ("search_modifications", {"query": "methyl"}, "results"),
    ],
)
def test_modomics_pages_are_recoverable(catalog, endpoint, base_arguments, key):
    response = Mock(status_code=200)
    response.json.return_value = catalog
    tool = MODOMICSTool({"name": "test", "fields": {"endpoint_type": endpoint}})

    with patch("tooluniverse.modomics_tool.requests.get", return_value=response):
        first = tool.run({**base_arguments, "limit": 3, "offset": 0})["data"]
        second = tool.run({**base_arguments, "limit": 3, "offset": 3})["data"]
        tail = tool.run({**base_arguments, "limit": 3, "offset": 6})["data"]

    assert [row["id"] for row in first[key]] == [0, 1, 2]
    assert [row["id"] for row in second[key]] == [3, 4, 5]
    assert [row["id"] for row in tail[key]] == [6]
    assert first["has_more"] is True
    assert first["next_offset"] == 3
    assert tail["has_more"] is False
    assert tail["next_offset"] is None
