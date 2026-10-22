from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.lipidmaps_tool import LipidMapsTool


pytestmark = pytest.mark.unit


def _tool(input_item="lm_id"):
    return LipidMapsTool({"fields": {"context": "compound", "input_item": input_item}})


def _response(payload, text="payload"):
    response = MagicMock()
    response.text = text
    response.json.return_value = payload
    return response


@pytest.mark.parametrize(
    "arguments,error",
    [
        ({"input_value": 1}, "input_value"),
        ({"input_value": "LMFA08040013", "output_item": "not_a_field"}, "output_item"),
        ({"input_value": "C00157", "xref_type": 1}, "xref_type"),
        (
            {
                "input_value": "C00157",
                "xref_type": "kegg_id",
                "input_item": "hmdb_id",
            },
            "Conflicting",
        ),
    ],
)
def test_invalid_controls_are_rejected_before_network(arguments, error):
    with patch("tooluniverse.lipidmaps_tool.requests.get") as get:
        result = _tool().run(arguments)
    assert result["status"] == "error"
    assert error in result["error"]
    get.assert_not_called()


def test_non_json_http_200_is_an_error_not_success_text():
    response = _response(None, text="This output item does not exist")
    response.json.side_effect = ValueError
    with patch("tooluniverse.lipidmaps_tool.requests.get", return_value=response):
        result = _tool()._make_request("compound/lm_id/X/all/json")
    assert result["status"] == "error"
    assert "non-JSON" in result["error"]


def test_rows_are_numeric_order_and_marked_complete():
    payload = {
        "Row10": {"lm_id": "LM10"},
        "Row2": {"lm_id": "LM2"},
        "Row1": {"lm_id": "LM1"},
    }
    with patch(
        "tooluniverse.lipidmaps_tool.requests.get",
        return_value=_response(payload),
    ):
        result = _tool()._make_request("compound/formula/C/all/json")
    assert [record["lm_id"] for record in result["data"]] == ["LM1", "LM2", "LM10"]
    assert result["metadata"]["result_set_complete"] is True


@pytest.mark.parametrize(
    "payload",
    [
        {"Row1": {"lm_id": "LM1"}, "warning": "partial"},
        {"RowX": {"lm_id": "LM1"}},
        {"Row1": None},
        [None],
        42,
    ],
)
def test_malformed_json_cannot_become_silent_partial_success(payload):
    with patch(
        "tooluniverse.lipidmaps_tool.requests.get",
        return_value=_response(payload),
    ):
        result = _tool()._make_request("compound/formula/C/all/json")
    assert result["status"] == "error"


def test_chain_abbreviation_is_normalized_before_first_request():
    with patch.object(
        LipidMapsTool,
        "_make_request",
        return_value={"status": "success", "data": [{"lm_id": "LMGP01012146"}]},
    ) as request:
        result = _tool("abbrev").run({"input_value": "PC 16:0/18:1"})
    path = request.call_args.args[0]
    assert "abbrev_chains" in path
    assert "PC%2016%3A0_18%3A1" in path
    request.assert_called_once()
    assert result["metadata"]["resolved_via"] == "abbrev_chains=PC 16:0_18:1"


def test_exact_lmid_response_is_verified():
    with patch.object(
        LipidMapsTool,
        "_make_request",
        return_value={
            "status": "success",
            "data": {"lm_id": "DIFFERENT"},
            "metadata": {"result_set_complete": True},
        },
    ):
        result = _tool().run({"input_value": "LMFA08040013"})
    assert result["status"] == "error"
    assert result["returned_lm_ids"] == ["DIFFERENT"]


def test_selected_output_field_is_explicitly_not_full_field_scope():
    with patch.object(
        LipidMapsTool,
        "_make_request",
        return_value={"status": "success", "data": {"name": "Palmitoyl-EA"}},
    ):
        result = _tool().run({"input_value": "LMFA08040013", "output_item": "name"})
    assert result["metadata"]["field_scope_complete"] is False
    assert result["metadata"]["output_item"] == "name"
