import gzip
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.hlaligandatlas_tool import HLALigandAtlasTool
from tooluniverse.mhcmotifatlas_tool import MHCMotifAtlasTool


pytestmark = pytest.mark.unit


def _response(*, content=b"", text="", status=200):
    response = MagicMock()
    response.content = content
    response.text = text
    response.status_code = status
    return response


def _hla_table(count):
    rows = ["ID\tPeptide\tClass\tDonor alleles\tTissues"]
    rows.extend(
        f"{index}\tPEPTIDE{index}\tHLA-I\ts/A*02:01\tLung" for index in range(count)
    )
    return gzip.compress(("\n".join(rows) + "\n").encode())


def _mhc_table(count):
    rows = ["Allele\tPeptide"]
    rows.extend(f"A0101\tPEPTIDE{index}" for index in range(count))
    return "\n".join(rows) + "\n"


def test_hla_filtered_matches_are_exactly_paginated():
    tool = HLALigandAtlasTool({"fields": {"operation": "get_benign_peptides"}})
    response = _response(content=_hla_table(5))
    with patch(
        "tooluniverse.hlaligandatlas_tool.request_with_retry",
        return_value=response,
    ):
        first = tool.run({"hla_class": "HLA-I", "limit": 2, "offset": 0})
        second = tool.run({"hla_class": "HLA-I", "limit": 2, "offset": 2})
    assert first["metadata"]["total_matches"] == 5
    assert first["metadata"]["next_offset"] == 2
    assert first["metadata"]["rows_scanned"] == 5
    assert {
        item["peptide_sequence_id"] for item in first["data"]["peptides"]
    }.isdisjoint(item["peptide_sequence_id"] for item in second["data"]["peptides"])


def test_hla_exact_limit_is_not_falsely_marked_truncated():
    tool = HLALigandAtlasTool({"fields": {"operation": "get_benign_peptides"}})
    with patch(
        "tooluniverse.hlaligandatlas_tool.request_with_retry",
        return_value=_response(content=_hla_table(2)),
    ):
        result = tool.run({"limit": 2})
    assert result["metadata"]["total_matches"] == 2
    assert result["metadata"]["truncated"] is False
    assert result["metadata"]["result_set_complete"] is True


@pytest.mark.parametrize("arguments", [{"limit": 0}, {"limit": "2"}, {"offset": -1}])
def test_hla_invalid_pagination_is_rejected_before_download(arguments):
    tool = HLALigandAtlasTool({"fields": {"operation": "get_benign_peptides"}})
    with patch("tooluniverse.hlaligandatlas_tool.request_with_retry") as get:
        result = tool.run(arguments)
    assert result["status"] == "error"
    get.assert_not_called()


def test_mhc_ligands_are_exactly_paginated():
    tool = MHCMotifAtlasTool({})
    with patch(
        "tooluniverse.mhcmotifatlas_tool.request_with_retry",
        return_value=_response(text=_mhc_table(5)),
    ):
        first = tool.run({"allele": "A0101", "limit": 2})
        second = tool.run({"allele": "A0101", "limit": 2, "offset": 2})
    assert first["metadata"]["total_matches"] == 5
    assert first["metadata"]["next_offset"] == 2
    assert {item["peptide"] for item in first["data"]["peptides"]}.isdisjoint(
        item["peptide"] for item in second["data"]["peptides"]
    )


def test_mhc_sequence_failure_is_explicit_partial_success():
    tool = MHCMotifAtlasTool({})
    with patch(
        "tooluniverse.mhcmotifatlas_tool.request_with_retry",
        side_effect=[
            _response(text=_mhc_table(2)),
            _response(status=503),
        ],
    ):
        result = tool.run({"allele": "A0101", "include_sequence": True})
    assert result["status"] == "success"
    assert result["metadata"]["sequence_found"] is False
    assert "503" in result["metadata"]["sequence_error"]
    assert result["metadata"]["requested_scope_complete"] is False


@pytest.mark.parametrize(
    "arguments",
    [
        {"allele": "A0101", "limit": 0},
        {"allele": "A0101", "limit": "2"},
        {"allele": "A0101", "offset": -1},
        {"allele": "A0101", "include_sequence": "false"},
    ],
)
def test_mhc_invalid_controls_are_rejected_before_download(arguments):
    tool = MHCMotifAtlasTool({})
    with patch("tooluniverse.mhcmotifatlas_tool.request_with_retry") as get:
        result = tool.run(arguments)
    assert result["status"] == "error"
    get.assert_not_called()
