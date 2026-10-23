from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.modomics_tool import MODOMICSTool


pytestmark = pytest.mark.unit


def _tool(endpoint):
    return MODOMICSTool({"fields": {"endpoint_type": endpoint}})


def _response(payload):
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = payload
    return response


def _catalog():
    return {
        "2": {"id": 2, "name": "first record", "reference_moiety": ["C"]},
        "78": {
            "id": 78,
            "name": "pseudouridine",
            "short_name": "Y",
            "formula": "C9H12N2O6",
            "reference_moiety": ["U"],
        },
    }


def test_detail_lookup_uses_exact_catalog_key_not_first_response_record():
    with patch(
        "tooluniverse.modomics_tool.requests.get", return_value=_response(_catalog())
    ) as get:
        result = _tool("get_modification").run({"modification_id": 78})
    assert get.call_args.args[0].endswith("/modifications")
    assert result["data"]["id"] == 78
    assert result["data"]["name"] == "pseudouridine"
    assert result["metadata"]["lookup_strategy"] == "exact_catalog_key"
    assert result["metadata"]["returned_modification_id"] == 78


def test_unknown_id_is_error_even_though_upstream_catalog_is_nonempty():
    with patch(
        "tooluniverse.modomics_tool.requests.get", return_value=_response(_catalog())
    ):
        result = _tool("get_modification").run({"modification_id": 999})
    assert result["status"] == "error"
    assert "No modification found" in result["error"]
    assert result["catalog_total"] == 2


def test_conflicting_catalog_key_and_embedded_id_is_explicit():
    with patch(
        "tooluniverse.modomics_tool.requests.get",
        return_value=_response({"78": {"id": 2, "name": "wrong"}}),
    ):
        result = _tool("get_modification").run({"modification_id": 78})
    assert result["status"] == "error"
    assert result["catalog_key"] == "78"
    assert result["embedded_id"] == 2


@pytest.mark.parametrize(
    "endpoint,arguments,error",
    [
        ("get_modification", {"modification_id": True}, "positive integer"),
        ("get_modification", {"modification_id": "78"}, "positive integer"),
        ("list_modifications", {"limit": 0}, "limit must be"),
        ("list_modifications", {"limit": 501}, "limit must be"),
        ("search_modifications", {"query": 78}, "non-empty string"),
        ("search_modifications", {"query": "methyl", "offset": -1}, "offset"),
    ],
)
def test_invalid_inputs_are_rejected_before_network(endpoint, arguments, error):
    with patch("tooluniverse.modomics_tool.requests.get") as get:
        result = _tool(endpoint).run(arguments)
    assert result["status"] == "error"
    assert error in result["error"]
    get.assert_not_called()


def test_list_order_is_numeric_and_deterministic():
    catalog = {
        "78": {"id": 78, "name": "last", "reference_moiety": []},
        "2": {"id": 2, "name": "first", "reference_moiety": []},
        "10": {"id": 10, "name": "middle", "reference_moiety": []},
    }
    with patch(
        "tooluniverse.modomics_tool.requests.get", return_value=_response(catalog)
    ):
        result = _tool("list_modifications").run({"limit": 2, "offset": 0})
    assert [record["id"] for record in result["data"]["modifications"]] == [2, 10]
    assert result["data"]["next_offset"] == 2
    assert result["data"]["result_set_complete"] is False
