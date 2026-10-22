import inspect
from unittest.mock import MagicMock, patch

from tooluniverse.rhea_tool import MAX_ROWS_PER_REQUEST, RheaTool
from tooluniverse.tools.Rhea_search_by_chebi import Rhea_search_by_chebi
from tooluniverse.tools.Rhea_search_by_ec import Rhea_search_by_ec
from tooluniverse.tools.Rhea_search_reactions import Rhea_search_reactions


def _tool():
    return RheaTool({"fields": {"endpoint": "search_by_chebi"}})


def _tsv(n):
    rows = ["Reaction identifier"]
    rows.extend(f"RHEA:{10000 + i}" for i in range(n))
    return "\n".join(rows)


def _fake_get(total):
    def fake_get(url, params=None, timeout=None):
        response = MagicMock()
        response.raise_for_status.return_value = None
        if "limit" not in params:
            response.text = _tsv(total)
        else:
            response.text = _tsv(min(total, params["limit"]))
        return response

    return fake_get


@patch("tooluniverse.rhea_tool.requests.get")
def test_common_chebi_query_is_recoverable_beyond_old_1000_row_window(mock_get):
    mock_get.side_effect = _fake_get(6724)

    result = _tool().run({"chebi_id": "CHEBI:15377", "limit": 3, "offset": 6000})

    assert [row["rhea_id"] for row in result["data"]] == [
        "RHEA:16000",
        "RHEA:16001",
        "RHEA:16002",
    ]
    assert mock_get.call_args.kwargs["params"]["limit"] == 6003
    assert result["metadata"]["total_results"] == 6724
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_offset"] == 6003
    assert result["metadata"]["database_result_complete"] is True
    assert MAX_ROWS_PER_REQUEST >= 6724


@patch("tooluniverse.rhea_tool.requests.get")
def test_rhea_final_deep_page_ends_cleanly(mock_get):
    mock_get.side_effect = _fake_get(6724)

    result = _tool().run({"chebi_id": "CHEBI:15377", "limit": 3, "offset": 6722})

    assert len(result["data"]) == 2
    assert result["metadata"]["has_more"] is False
    assert result["metadata"]["next_offset"] is None


def test_generated_rhea_wrappers_expose_offset():
    for function in (
        Rhea_search_reactions,
        Rhea_search_by_chebi,
        Rhea_search_by_ec,
    ):
        parameters = inspect.signature(function).parameters
        assert parameters["limit"].default == 20
        assert parameters["offset"].default == 0
