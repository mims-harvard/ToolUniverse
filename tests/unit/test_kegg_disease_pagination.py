from unittest.mock import MagicMock, patch

from tooluniverse.kegg_ext_tool import KEGGExtTool


def _tool():
    return KEGGExtTool(
        {"name": "KEGG_search_disease", "fields": {"endpoint": "search_disease"}}
    )


def _response(count=5):
    response = MagicMock()
    response.text = "\n".join(
        f"ds:H{index:05d}\tDisease {index}" for index in range(count)
    )
    response.raise_for_status.return_value = None
    return response


@patch("tooluniverse.kegg_ext_tool.requests.get", return_value=_response())
def test_kegg_disease_reports_unsliced_total_and_adjacent_page(_get):
    result = _tool().run({"keyword": "cancer", "max_results": 2, "offset": 2})

    assert [row["disease_id"] for row in result["data"]] == ["H00002", "H00003"]
    assert result["metadata"]["total"] == 5
    assert result["metadata"]["returned"] == 2
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_offset"] == 4


@patch("tooluniverse.kegg_ext_tool.requests.get", return_value=_response())
def test_kegg_disease_tail_page_terminates(_get):
    result = _tool().run({"keyword": "cancer", "max_results": 2, "offset": 4})

    assert [row["disease_id"] for row in result["data"]] == ["H00004"]
    assert result["metadata"]["has_more"] is False
    assert result["metadata"]["next_offset"] is None
