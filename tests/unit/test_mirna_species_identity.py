"""Regression tests for species identity in RNAcentral detail tools."""

from unittest.mock import Mock, patch

import pytest

from tooluniverse.mirna_tool import miRNAGetTool


BASE_ID = "URS000039ED8D"


def _tool() -> miRNAGetTool:
    return miRNAGetTool(
        {
            "name": "miRBase_get_mirna",
            "fields": {"endpoint": "get_rna"},
            "timeout": 30,
        }
    )


def _response(payload):
    response = Mock()
    response.status_code = 200
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


def _human_record(**overrides):
    record = {
        "rnacentral_id": f"{BASE_ID}_9606",
        "description": "Homo sapiens (human) hsa-miR-21-5p",
        "short_description": "(human) hsa-miR-21-5p",
        "sequence": "UAGCUUAUCAGACUGAUGUUGA",
        "length": 22,
        "rna_type": "miRNA",
        "species": "Homo sapiens",
        "taxid": 9606,
        "genes": [],
        "publications": 28263,
        "is_active": True,
        "distinct_databases": "ENA,MIRBASE,RefSeq",
    }
    record.update(overrides)
    return record


@patch("tooluniverse.mirna_tool.requests.get")
def test_base_id_plus_taxid_queries_canonical_species_record(mock_get):
    mock_get.return_value = _response(_human_record())

    result = _tool().run({"rnacentral_id": BASE_ID, "taxid": 9606})

    assert result["status"] == "success"
    assert result["data"]["rnacentral_id"] == f"{BASE_ID}_9606"
    assert result["data"]["taxid"] == 9606
    assert result["data"]["species"] == "Homo sapiens"
    assert result["data"]["rna_type"] == "miRNA"
    assert result["metadata"]["identity_verified"] is True
    mock_get.assert_called_once_with(
        f"https://rnacentral.org/api/v1/rna/{BASE_ID}_9606/?format=json",
        timeout=30,
    )


@patch("tooluniverse.mirna_tool.requests.get")
def test_species_suffix_is_not_sent_to_nonexistent_xrefs_endpoint(mock_get):
    mock_get.return_value = _response(_human_record())

    result = _tool().run({"rnacentral_id": f"{BASE_ID}_9606"})

    assert result["status"] == "success"
    assert result["data"]["species"] == "Homo sapiens"
    assert result["data"]["taxid"] == 9606
    assert mock_get.call_count == 1
    assert "/xrefs/" not in mock_get.call_args.args[0]


@patch("tooluniverse.mirna_tool.requests.get")
def test_conflicting_suffix_and_taxid_fail_before_network(mock_get):
    result = _tool().run(
        {"rnacentral_id": f"{BASE_ID}_9606", "taxid": 10090}
    )

    assert result["status"] == "error"
    assert "Conflicting taxids" in result["error"]
    mock_get.assert_not_called()


@pytest.mark.parametrize("taxid", [True, 0, -1, "9606", 9606.0])
@patch("tooluniverse.mirna_tool.requests.get")
def test_invalid_taxid_is_not_silently_coerced(mock_get, taxid):
    result = _tool().run({"rnacentral_id": BASE_ID, "taxid": taxid})

    assert result["status"] == "error"
    assert result["parameter"] == "taxid"
    mock_get.assert_not_called()


@pytest.mark.parametrize(
    "rnacentral_id", ["", "not-an-id", "URS123", "URS000039ED8D_0"]
)
@patch("tooluniverse.mirna_tool.requests.get")
def test_invalid_rnacentral_id_fails_before_network(mock_get, rnacentral_id):
    result = _tool().run({"rnacentral_id": rnacentral_id})

    assert result["status"] == "error"
    assert result["parameter"] == "rnacentral_id"
    mock_get.assert_not_called()


@patch("tooluniverse.mirna_tool.requests.get")
def test_mismatched_upstream_identity_is_an_error(mock_get):
    mock_get.return_value = _response(
        _human_record(rnacentral_id="URS0000416056_9606")
    )

    result = _tool().run({"rnacentral_id": BASE_ID, "taxid": 9606})

    assert result["status"] == "error"
    assert "identity does not match" in result["error"]


@patch("tooluniverse.mirna_tool.requests.get")
def test_unknown_taxid_reports_the_canonical_species_record(mock_get):
    response = Mock()
    response.status_code = 404
    mock_get.return_value = response

    result = _tool().run({"rnacentral_id": BASE_ID, "taxid": 999999999})

    assert result["status"] == "error"
    assert "species-specific record not found" in result["error"]
    assert f"{BASE_ID}_999999999" in result["error"]
    response.raise_for_status.assert_not_called()


@patch("tooluniverse.mirna_tool.requests.get")
def test_mismatched_upstream_taxid_is_an_error(mock_get):
    mock_get.return_value = _response(_human_record(taxid=10090))

    result = _tool().run({"rnacentral_id": BASE_ID, "taxid": 9606})

    assert result["status"] == "error"
    assert "taxid does not match" in result["error"]


@patch("tooluniverse.mirna_tool.requests.get")
def test_bare_urs_does_not_invent_a_species_or_zero_publications(mock_get):
    mock_get.return_value = _response(
        {
            "rnacentral_id": BASE_ID,
            "description": "ncRNA from 30 species",
            "short_description": None,
            "sequence": "UAGCUUAUCAGACUGAUGUUGA",
            "length": 22,
            "rna_type": "ncRNA",
            "species": None,
            "taxid": None,
            "genes": None,
            "publications": (
                f"https://rnacentral.org/api/v1/rna/{BASE_ID}/publications"
            ),
            "is_active": True,
            "distinct_databases": ["ENA", "MIRBASE"],
        }
    )

    result = _tool().run({"rnacentral_id": BASE_ID})

    assert result["status"] == "success"
    assert result["data"]["species"] == ""
    assert result["data"]["taxid"] is None
    assert result["data"]["rna_type"] == "ncRNA"
    assert result["data"]["genes"] == []
    assert result["data"]["publications_count"] is None
    assert result["metadata"]["species_specific"] is False
