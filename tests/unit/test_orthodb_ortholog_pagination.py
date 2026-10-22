from unittest.mock import Mock

from tooluniverse.orthodb_tool import OrthoDBTool


def test_orthologs_fetch_large_window_and_page_locally(monkeypatch) -> None:
    header = (
        "pub_og_id\tog_name\tlevel_taxid\torganism_taxid\torganism_name"
        "\tpub_gene_id\tdescription"
    )
    rows = [
        f"group\tBRCA2\t2759\t{index}_0\tSpecies {index}\tgene{index}\tdesc{index}"
        for index in range(5)
    ]
    response = Mock(text="\n".join([header, *rows]))
    response.raise_for_status.return_value = None
    get = Mock(return_value=response)
    monkeypatch.setattr("tooluniverse.orthodb_tool.requests.get", get)
    tool = OrthoDBTool({"fields": {"endpoint": "orthologs"}})

    result = tool.run(
        {
            "group_id": "794361at2759",
            "species": "9606",
            "limit": 2,
            "offset": 2,
        }
    )

    assert get.call_args.kwargs["params"] == {
        "id": "794361at2759",
        "limit": 5000,
        "species": "9606",
    }
    data = result["data"]
    assert data["total_orthologs"] == 5
    assert data["returned"] == 2
    assert [row["gene_id"] for row in data["orthologs"]] == ["gene2", "gene3"]
    assert data["has_more"] is True
    assert data["next_offset"] == 4
    assert result["metadata"]["total_is_lower_bound"] is False
    assert result["metadata"]["api_result_window_limit"] == 5000
    assert result["metadata"]["accessible_window_complete"] is True
    assert data["result_set_complete"] is False


def test_orthologs_rejects_coerced_or_clamped_pagination(monkeypatch) -> None:
    get = Mock()
    monkeypatch.setattr("tooluniverse.orthodb_tool.requests.get", get)
    tool = OrthoDBTool({"fields": {"endpoint": "orthologs"}})

    for pagination in (
        {"limit": "2"},
        {"limit": True},
        {"limit": 0},
        {"limit": 1001},
        {"offset": "2"},
        {"offset": -1},
        {"offset": False},
    ):
        result = tool.run({"group_id": "794361at2759", **pagination})
        assert result["status"] == "error", pagination

    get.assert_not_called()
