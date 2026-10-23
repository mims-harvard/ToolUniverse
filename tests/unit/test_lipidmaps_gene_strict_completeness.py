from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.lipidmaps_gene_tool import LipidMapsGeneTool


pytestmark = pytest.mark.unit


def _tool(context="gene", input_item="gene_symbol"):
    return LipidMapsGeneTool({"fields": {"context": context, "input_item": input_item}})


def _response(payload, text="payload"):
    response = MagicMock()
    response.text = text
    response.json.return_value = payload
    return response


@pytest.mark.parametrize(
    "arguments,error",
    [
        ({"input_value": 2194}, "input_value"),
        ({"input_value": "FASN", "input_item": 1}, "input_item"),
        ({"input_value": "FASN", "input_item": "uniprot_id"}, "Unsupported input_item"),
        ({"input_value": "FASN", "output_item": 1}, "output_item"),
        (
            {"input_value": "FASN", "output_item": "not_a_field"},
            "Unsupported output_item",
        ),
    ],
)
def test_invalid_controls_are_rejected_before_network(arguments, error):
    with patch("tooluniverse.lipidmaps_gene_tool.requests.get") as get:
        result = _tool().run(arguments)
    assert result["status"] == "error"
    assert error in result["error"]
    get.assert_not_called()


def test_row_keys_are_sorted_numerically_and_complete():
    payload = {
        "Row10": {"gene_symbol": "TEN"},
        "Row2": {"gene_symbol": "TWO"},
        "Row1": {"gene_symbol": "ONE"},
    }
    with patch(
        "tooluniverse.lipidmaps_gene_tool.requests.get",
        return_value=_response(payload),
    ):
        result = _tool().run({"input_value": "FASN"})
    assert [record["gene_symbol"] for record in result["data"]] == [
        "ONE",
        "TWO",
        "TEN",
    ]
    assert result["metadata"]["total_results"] == 3
    assert result["metadata"]["result_set_complete"] is True
    assert result["metadata"]["field_scope_complete"] is True


def test_single_output_field_is_explicitly_not_full_field_scope():
    payload = {"Row1": {"gene_symbol": "FASN", "gene_name": "fatty acid synthase"}}
    with patch(
        "tooluniverse.lipidmaps_gene_tool.requests.get",
        return_value=_response(payload),
    ):
        result = _tool().run({"input_value": "FASN", "output_item": "gene_name"})
    assert result["metadata"]["result_set_complete"] is True
    assert result["metadata"]["field_scope_complete"] is False
    assert result["metadata"]["output_item"] == "gene_name"


@pytest.mark.parametrize(
    "payload",
    [
        [None],
        {"Row1": {"gene_symbol": "FASN"}, "warning": "partial"},
        {"RowX": {"gene_symbol": "FASN"}},
        {"Row1": None},
        42,
    ],
)
def test_malformed_payload_cannot_become_silent_partial_success(payload):
    with patch(
        "tooluniverse.lipidmaps_gene_tool.requests.get",
        return_value=_response(payload),
    ):
        result = _tool().run({"input_value": "FASN"})
    assert result["status"] == "error"
    assert "LIPID MAPS" in result["error"]


def test_input_path_segment_is_url_encoded():
    with patch(
        "tooluniverse.lipidmaps_gene_tool.requests.get",
        return_value=_response([], text="[]"),
    ) as get:
        result = _tool().run({"input_value": "FASN/test"})
    assert "FASN%2Ftest" in get.call_args.args[0]
    assert result["metadata"]["result_set_complete"] is True


def test_protein_output_namespace_accepts_sequence_but_gene_does_not():
    with patch("tooluniverse.lipidmaps_gene_tool.requests.get") as get:
        gene_result = _tool().run({"input_value": "FASN", "output_item": "seq"})
    assert gene_result["status"] == "error"
    get.assert_not_called()

    with patch(
        "tooluniverse.lipidmaps_gene_tool.requests.get",
        return_value=_response({"seq": "MEEV"}),
    ):
        protein_result = _tool("protein", "uniprot_id").run(
            {"input_value": "P49327", "output_item": "seq"}
        )
    assert protein_result["status"] == "success"
    assert protein_result["data"] == [{"seq": "MEEV"}]
