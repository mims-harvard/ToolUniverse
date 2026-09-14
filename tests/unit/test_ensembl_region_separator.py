"""Regression tests for Ensembl region-coordinate normalization."""

from unittest.mock import patch

from tooluniverse.ensembl_sequence_tool import EnsemblSequenceTool


def _tool():
    return EnsemblSequenceTool({"fields": {"endpoint": "region_sequence"}})


def _response():
    response = type("Response", (), {})()
    response.raise_for_status = lambda: None
    response.json = lambda: {"seq": "ACTG", "molecule": "dna", "id": "17:1..4"}
    return response


def test_region_sequence_preserves_reverse_strand_with_canonical_separator():
    with patch(
        "tooluniverse.ensembl_sequence_tool.requests.get", return_value=_response()
    ) as get:
        result = _tool().run({"region": "17:7668421..7668520:-1"})

    assert result["status"] == "success"
    assert result["data"]["region"] == "17:7668421..7668520:-1"
    assert get.call_args.args[0].endswith("/17:7668421..7668520:-1")


def test_region_sequence_converts_hyphen_coordinate_separator_on_forward_strand():
    with patch(
        "tooluniverse.ensembl_sequence_tool.requests.get", return_value=_response()
    ) as get:
        result = _tool().run({"region": "17:7668421-7668520"})

    assert result["status"] == "success"
    assert result["data"]["region"] == "17:7668421..7668520:1"
    assert get.call_args.args[0].endswith("/17:7668421..7668520:1")


def test_region_sequence_preserves_hyphenated_contig_name():
    with patch(
        "tooluniverse.ensembl_sequence_tool.requests.get", return_value=_response()
    ) as get:
        result = _tool().run({"region": "contig-name:100-200:-1"})

    assert result["status"] == "success"
    assert result["data"]["region"] == "contig-name:100..200:-1"
    assert get.call_args.args[0].endswith("/contig-name:100..200:-1")
