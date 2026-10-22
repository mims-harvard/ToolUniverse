from unittest.mock import Mock, patch

import pytest

from tooluniverse.togoid_tool import TogoIDConvertTool, TogoIDDatasetsTool


def _response(payload):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload
    return response


def _convert_tool():
    return TogoIDConvertTool({"name": "TogoID_convert", "fields": {"timeout": 30}})


def _datasets_tool():
    return TogoIDDatasetsTool(
        {"name": "TogoID_list_datasets", "fields": {"timeout": 30}}
    )


@pytest.mark.parametrize(
    "arguments",
    [
        {"ids": "A", "source": "x"},
        {"ids": ["A"], "source": "x", "target": "y"},
        {"ids": "A,,B", "source": "x", "target": "y"},
        {"ids": "A,A", "source": "x", "target": "y"},
        {"ids": "A", "source": "x-y", "target": "y"},
        {"ids": "A", "source": "x", "target": "y", "format": "json"},
        {
            "ids": ",".join(f"ID{i}" for i in range(51)),
            "source": "x",
            "target": "y",
        },
    ],
)
def test_invalid_conversion_inputs_are_rejected_without_network(arguments):
    with patch("tooluniverse.togoid_tool.requests.get") as get:
        result = _convert_tool().run(arguments)

    assert result["status"] == "error"
    get.assert_not_called()


def test_multi_input_conversion_preserves_each_mapping_and_unmapped_ids():
    outputs = {
        "ENSG00000139618": ["P51587", "H0YD86"],
        "ENSG00000012048": ["P38398", "H0YD86"],
        "ENSG_NOT_REAL": [],
    }

    def get(_url, params, **_kwargs):
        input_id = params["ids"]
        return _response(
            {
                "ids": [input_id],
                "results": outputs[input_id],
                "route": ["ensembl_gene", "uniprot"],
            }
        )

    with patch("tooluniverse.togoid_tool.requests.get", side_effect=get) as request:
        result = _convert_tool().run(
            {
                "ids": "ENSG00000139618, ENSG00000012048, ENSG_NOT_REAL",
                "source": "ensembl_gene",
                "target": "uniprot",
            }
        )

    assert result["status"] == "success"
    data = result["data"]
    assert [mapping["input_id"] for mapping in data["mappings"]] == list(outputs)
    assert data["mappings"][0]["converted_ids"] == ["P51587", "H0YD86"]
    assert data["mappings"][1]["converted_ids"] == ["P38398", "H0YD86"]
    assert data["mappings"][2]["mapped"] is False
    assert data["converted_ids"] == ["P51587", "H0YD86", "P38398"]
    assert data["unmapped_ids"] == ["ENSG_NOT_REAL"]
    assert data["mapped_input_count"] == 2
    assert data["all_inputs_mapped"] is False
    assert data["total_associations"] == 4
    assert result["metadata"]["mapping_complete"] is True
    assert result["metadata"]["request_count"] == 3
    assert request.call_count == 3


def test_conversion_rejects_mismatched_input_or_route_echo():
    payload = {
        "ids": ["DIFFERENT"],
        "results": ["P51587"],
        "route": ["ensembl_gene", "uniprot"],
    }
    with patch(
        "tooluniverse.togoid_tool.requests.get", return_value=_response(payload)
    ):
        result = _convert_tool().run(
            {
                "ids": "ENSG00000139618",
                "source": "ensembl_gene",
                "target": "uniprot",
            }
        )

    assert result["status"] == "error"
    assert "mismatched data" in result["error"]


def test_dataset_listing_preserves_complete_records_and_global_count():
    source = {
        "ensembl_gene": {
            "label": "Ensembl gene",
            "category": "Gene",
            "catalog": "nbdc00054",
            "regex": "^ENS",
            "annotations": [{"label": "Chromosome", "variable": "chromosome"}],
            "examples": [["ENSG00000139618"]],
            "prefix": [{"label": "Ensembl", "uri": "https://ensembl.org/id/"}],
            "future_field": {"preserved": True},
        },
        "uniprot": {
            "label": "UniProt",
            "category": "Protein",
            "catalog": "nbdc00221",
        },
    }
    with patch("tooluniverse.togoid_tool.requests.get", return_value=_response(source)):
        result = _datasets_tool().run({"category": "gene"})

    assert result["status"] == "success"
    assert len(result["data"]) == 1
    dataset = result["data"][0]
    assert dataset["dataset"] == "ensembl_gene"
    assert dataset["regex"] == "^ENS"
    assert dataset["annotations"] == source["ensembl_gene"]["annotations"]
    assert dataset["prefixes"] == source["ensembl_gene"]["prefix"]
    assert dataset["record"] == source["ensembl_gene"]
    assert dataset["record"]["future_field"] == {"preserved": True}
    assert result["metadata"]["total"] == 1
    assert result["metadata"]["total_available"] == 2
    assert result["metadata"]["category_filter"] == "Gene"
    assert result["metadata"]["result_set_complete"] is True


def test_unknown_dataset_category_is_not_silent_empty_success():
    source = {
        "ensembl_gene": {"label": "Ensembl gene", "category": "Gene"},
        "uniprot": {"label": "UniProt", "category": "Protein"},
    }
    with patch("tooluniverse.togoid_tool.requests.get", return_value=_response(source)):
        result = _datasets_tool().run({"category": "Genes"})

    assert result["status"] == "error"
    assert result["available_categories"] == ["Gene", "Protein"]
