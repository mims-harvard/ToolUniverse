from unittest.mock import Mock, patch

import pytest

from tooluniverse.harmonizome_tool import HarmonizomeTool


def _response(body):
    response = Mock(status_code=200)
    response.json.return_value = body
    response.raise_for_status.return_value = None
    return response


@pytest.mark.parametrize("entity_type", ["dataset", "attribute"])
def test_harmonizome_search_pages_are_recoverable(entity_type):
    if entity_type == "dataset":
        body = {"entities": [{"name": f"Expression {i}"} for i in range(7)]}
    else:
        body = [f"kinase-{i}" for i in range(7)]
    tool = HarmonizomeTool({"name": "test", "fields": {"endpoint": "search"}})
    with patch("tooluniverse.harmonizome_tool.requests.get", return_value=_response(body)):
        first = tool.run({"query": "expression", "entity_type": entity_type, "limit": 3})
        second = tool.run(
            {"query": "expression", "entity_type": entity_type, "limit": 3, "offset": 3}
        )
        tail = tool.run(
            {"query": "expression", "entity_type": entity_type, "limit": 3, "offset": 6}
        )
    assert len(first["data"]) == 3
    assert first["metadata"]["next_offset"] == 3
    assert first["metadata"]["has_more"] is True
    assert len(second["data"]) == 3
    assert len(tail["data"]) == 1
    assert tail["metadata"]["has_more"] is False


@pytest.mark.parametrize("mode", ["gene_set", "gene"])
def test_harmonizome_associations_have_offsets(mode):
    associations = []
    for i in range(7):
        associations.append(
            {
                "gene": {"symbol": f"G{i}"},
                "geneSet": {"name": f"SET{i}"},
                "thresholdValue": i,
            }
        )
    body = {"symbol": "TP53", "associations": associations}
    arguments = {"mode": mode, "limit": 3, "offset": 3}
    if mode == "gene":
        arguments["gene_symbol"] = "TP53"
    else:
        arguments.update(attribute="heart", dataset="GTEx Tissue Gene Expression Profiles")
    tool = HarmonizomeTool(
        {"name": "test", "fields": {"endpoint": "get_gene_set_members"}}
    )
    with patch("tooluniverse.harmonizome_tool.requests.get", return_value=_response(body)):
        result = tool.run(arguments)
    key = "associations" if mode == "gene" else "members"
    assert len(result["data"][key]) == 3
    assert result["metadata"]["offset"] == 3
    assert result["metadata"]["next_offset"] == 6


def test_dataset_gene_sets_have_recoverable_offsets():
    body = {
        "name": "CTD Gene-Disease Associations",
        "geneSets": [{"name": f"Disease {i}/detail"} for i in range(7)],
    }
    tool = HarmonizomeTool(
        {"name": "test", "fields": {"endpoint": "get_dataset"}}
    )
    with patch(
        "tooluniverse.harmonizome_tool.requests.get", return_value=_response(body)
    ):
        result = tool.run({"dataset_name": body["name"], "gene_set_limit": 3, "gene_set_offset": 3})
    assert [row["name"] for row in result["data"]["gene_sets"]] == [
        "Disease 3",
        "Disease 4",
        "Disease 5",
    ]
    assert result["metadata"]["total_gene_sets"] == 7
    assert result["metadata"]["next_gene_set_offset"] == 6
    assert result["metadata"]["has_more_gene_sets"] is True


@pytest.mark.parametrize(
    "arguments",
    [
        {"dataset_name": "x", "gene_set_limit": 0},
        {"dataset_name": "x", "gene_set_limit": 1001},
        {"dataset_name": "x", "gene_set_offset": -1},
    ],
)
def test_dataset_gene_set_pagination_rejects_invalid_values(arguments):
    result = HarmonizomeTool(
        {"name": "test", "fields": {"endpoint": "get_dataset"}}
    ).run(arguments)
    assert result["status"] == "error"
