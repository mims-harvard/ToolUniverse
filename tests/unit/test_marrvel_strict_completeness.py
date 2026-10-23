from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.marrvel_tool import MARRVELGeneTool, MARRVELOmimTool


pytestmark = pytest.mark.unit


def _response(payload, status=200):
    response = MagicMock(status_code=status)
    response.json.return_value = payload
    return response


def _gene():
    return {
        "symbol": "CFTR",
        "name": "CF transmembrane conductance regulator",
        "description": "CF transmembrane conductance regulator",
        "entrezId": 1080,
        "hgncId": 1884,
        "uniprotKBId": "P13569",
        "taxonId": 9606,
        "chr": "7",
        "location": "7q31.2",
        "grch38Start": 117287120,
        "grch38Stop": 117715971,
        "grch39Stop": 117715971,
        "hg19Chr": "7",
        "hg19Start": 117105838,
        "hg19Stop": 117356025,
        "type": "protein-coding",
        "alias": ["ABCC7"],
        "prevSymbols": ["CF"],
        "entrezSummary": "summary",
        "status": "O",
        "lastModified": "20241028",
        "pharosLigandsIds": [71658],
        "pharosLegandsIds": [71658],
        "pharosTargetIds": [6580],
        "xref": {"hgncId": "1884", "ensemblId": "ENSG00000001626"},
    }


@pytest.mark.parametrize(
    "arguments,error",
    [
        ({}, "required"),
        ({"symbol": 1}, "non-empty string"),
        ({"symbol": " "}, "non-empty string"),
        ({"symbol": "CFTR", "gene": "BRCA1"}, "Conflicting"),
    ],
)
def test_gene_rejects_invalid_or_conflicting_aliases_before_network(arguments, error):
    with patch("tooluniverse.marrvel_tool.requests.get") as get:
        result = MARRVELGeneTool({}).run(arguments)
    assert result["status"] == "error"
    assert error in result["error"]
    get.assert_not_called()


def test_gene_preserves_coordinates_status_and_pharos_fields():
    with patch(
        "tooluniverse.marrvel_tool.requests.get", return_value=_response(_gene())
    ):
        result = MARRVELGeneTool({}).run({"symbol": "cftr", "gene": "CFTR"})
    data = result["data"]
    assert data["hgnc_id"] == "1884"
    assert data["grch38_start"] == 117287120
    assert data["hg19_stop"] == 117356025
    assert data["status"] == "O"
    assert data["last_modified"] == "20241028"
    assert data["pharos_ligand_ids"] == [71658]
    assert data["pharos_target_ids"] == [6580]
    assert result["metadata"]["returned_symbol_verified"] is True
    assert result["metadata"]["source_record_complete"] is True
    assert result["metadata"]["transport_security"] == "unencrypted_http_upstream"


def test_lowercase_symbol_is_uppercased_in_request_to_avoid_silent_empty_result():
    with patch(
        "tooluniverse.marrvel_tool.requests.get", return_value=_response(_gene())
    ) as get:
        result = MARRVELGeneTool({}).run({"symbol": "cftr"})
    assert "/symbol/CFTR" in get.call_args.args[0]
    assert result["status"] == "success"
    assert result["metadata"]["query_symbol"] == "CFTR"


def test_gene_rejects_returned_symbol_mismatch():
    record = _gene()
    record["symbol"] = "BRCA1"
    with patch(
        "tooluniverse.marrvel_tool.requests.get", return_value=_response(record)
    ):
        result = MARRVELGeneTool({}).run({"symbol": "CFTR"})
    assert result["status"] == "error"
    assert result["returned_symbol"] == "BRCA1"


def test_gene_rejects_conflicting_duplicate_identifiers():
    record = _gene()
    record["xref"]["hgncId"] = "9999"
    with patch(
        "tooluniverse.marrvel_tool.requests.get", return_value=_response(record)
    ):
        result = MARRVELGeneTool({}).run({"symbol": "CFTR"})
    assert result["status"] == "error"
    assert "conflicting HGNC" in result["error"]


def test_omim_preserves_mapping_and_top_level_qualifiers():
    payload = {
        "mimNumber": 602421,
        "title": "CFTR",
        "description": "OMIM description",
        "status": "live",
        "lastUpdate": "2026-08-06T09:28:08.249Z",
        "phenotypes": [
            {
                "mimNumber": 602421,
                "phenotype": "Cystic fibrosis",
                "phenotypeMimNumber": 219700,
                "phenotypeInheritance": "Autosomal recessive",
                "phenotypeMappingKey": 3,
                "phenotypicSeriesNumber": "PS219700",
            }
        ],
        "allelicVariants": [{"number": 1}, {"number": 2}],
    }
    with patch(
        "tooluniverse.marrvel_tool.requests.get", return_value=_response(payload)
    ):
        result = MARRVELOmimTool({}).run({"gene_symbol": "CFTR"})
    assert result["data"][0]["phenotype_mapping_key"] == 3
    assert result["metadata"]["omim_record"]["gene_mim_number"] == 602421
    assert result["metadata"]["phenotype_records_complete"] is True
    assert result["metadata"]["allelic_variant_count"] == 2
    assert result["metadata"]["allelic_variants_returned"] is False


@pytest.mark.parametrize(
    "payload",
    [42, {"phenotypes": {}, "allelicVariants": []}, {"phenotypes": [None]}],
)
def test_omim_rejects_malformed_payload_instead_of_silent_empty(payload):
    with patch(
        "tooluniverse.marrvel_tool.requests.get", return_value=_response(payload)
    ):
        result = MARRVELOmimTool({}).run({"symbol": "CFTR"})
    assert result["status"] == "error"
    assert "MARRVEL returned" in result["error"]
