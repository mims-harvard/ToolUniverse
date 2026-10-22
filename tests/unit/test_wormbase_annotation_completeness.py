from unittest.mock import MagicMock, patch

from tooluniverse.wormbase_tool import WormBaseTool


def _tool(endpoint):
    return WormBaseTool(
        {"name": f"WormBase_{endpoint}", "fields": {"endpoint_type": endpoint}}
    )


def _response(fields):
    response = MagicMock()
    response.json.return_value = {"fields": fields}
    return response


def test_phenotype_arrays_are_not_hard_truncated():
    observed = [
        {"phenotype": {"id": f"WBPhenotype:{i}", "label": f"Observed {i}"}}
        for i in range(125)
    ]
    not_observed = [
        {"phenotype": {"id": f"WBPhenotype:N{i}", "label": f"Absent {i}"}}
        for i in range(56)
    ]
    fields = {
        "name": {"data": {"label": "unc-26"}},
        "phenotype": {"data": observed},
        "phenotype_not_observed": {"data": not_observed},
    }

    with patch(
        "tooluniverse.wormbase_tool.requests.get", return_value=_response(fields)
    ):
        result = _tool("gene_phenotypes").run({"gene_id": "WBGene00006763"})

    assert result["data"]["phenotype_count"] == 125
    assert result["data"]["phenotypes_returned"] == 125
    assert len(result["data"]["phenotypes"]) == 125
    assert result["data"]["not_observed_count"] == 56
    assert len(result["data"]["phenotypes_not_observed"]) == 56


def test_expression_clusters_are_not_hard_truncated():
    clusters = [
        {"expression_cluster": {"id": f"cluster-{i}", "label": f"Cluster {i}"}}
        for i in range(142)
    ]
    fields = {
        "name": {"data": {"label": "unc-26"}},
        "expressed_in": {"data": []},
        "expressed_during": {"data": []},
        "subcellular_localization": {"data": []},
        "expression_cluster": {"data": clusters},
    }

    with patch(
        "tooluniverse.wormbase_tool.requests.get", return_value=_response(fields)
    ):
        result = _tool("gene_expression").run({"gene_id": "WBGene00006763"})

    assert result["data"]["expression_clusters_count"] == 142
    assert result["data"]["expression_clusters_returned"] == 142
    assert len(result["data"]["expression_clusters"]) == 142
