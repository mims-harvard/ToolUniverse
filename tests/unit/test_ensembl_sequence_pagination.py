"""Regression tests for recoverable Ensembl sequence pages."""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.ensembl_sequence_tool import EnsemblSequenceTool


pytestmark = pytest.mark.unit


def _response(sequence):
    response = MagicMock()
    response.json.return_value = {"id": "test", "molecule": "dna", "seq": sequence}
    return response


def _tool(endpoint):
    return EnsemblSequenceTool({"fields": {"endpoint": endpoint}})


def test_region_sequence_middle_and_tail_pages_are_reachable():
    tool = _tool("region_sequence")
    with patch("tooluniverse.ensembl_sequence_tool.requests.get", return_value=_response("ABCDEFGHIJKL")):
        middle = tool.run({"region": "1:1-12", "max_length": 5, "sequence_offset": 5})
        tail = tool.run({"region": "1:1-12", "max_length": 5, "sequence_offset": 10})

    assert middle["data"]["sequence"] == "FGHIJ"
    assert middle["data"]["sequence_length"] == 12
    assert middle["data"]["next_sequence_offset"] == 10
    assert tail["data"]["sequence"] == "KL"
    assert tail["data"]["has_more"] is False
    assert tail["data"]["next_sequence_offset"] is None


def test_id_type_is_auto_detected_when_omitted():
    tool = _tool("id_sequence")
    with patch("tooluniverse.ensembl_sequence_tool.requests.get", return_value=_response("ACGT")) as get:
        tool.run({"ensembl_id": "ENSG00000141510"})

    assert get.call_args.kwargs["params"]["type"] == "genomic"


@pytest.mark.parametrize(
    "arguments, message",
    [
        ({"max_length": 0}, "max_length"),
        ({"max_length": True}, "max_length"),
        ({"sequence_offset": -1}, "sequence_offset"),
        ({"sequence_offset": True}, "sequence_offset"),
    ],
)
def test_invalid_pagination_is_rejected_before_request(arguments, message):
    tool = _tool("region_sequence")
    with patch("tooluniverse.ensembl_sequence_tool.requests.get") as get:
        result = tool.run({"region": "1:1-12", **arguments})

    assert result["status"] == "error"
    assert message in result["error"]
    get.assert_not_called()
