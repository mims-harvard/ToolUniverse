from unittest.mock import MagicMock, patch

from tooluniverse.orthodb_tool import OrthoDBTool


def _json_response(payload):
    response = MagicMock(status_code=200)
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


def _tab_response(group_id):
    response = MagicMock(status_code=200)
    response.text = (
        "pub_og_id\tog_name\tlevel_taxid\n"
        f"{group_id}\tname-{group_id}\t7742\n"
    )
    return response


def test_search_uses_skip_and_authoritative_count():
    tool = OrthoDBTool({"fields": {"endpoint": "search"}})
    search = _json_response(
        {"data": ["g3", "g4", "g5", "g6"], "count": "15115"}
    )
    with patch(
        "tooluniverse.orthodb_tool.requests.get",
        side_effect=[search, _tab_response("g3"), _tab_response("g4")],
    ) as request:
        result = tool._search({"query": "BRCA1", "limit": 2, "offset": 3})

    assert request.call_args_list[0].kwargs["params"] == {
        "query": "BRCA1",
        "limit": 100,
        "skip": 3,
    }
    assert [row["group_id"] for row in result["data"]["groups"]] == ["g3", "g4"]
    assert result["data"]["total_groups"] == 15115
    assert result["data"]["next_offset"] == 5


def test_group_reads_current_v12_annotation_schema_without_truncation():
    go = lambda go_id, description: {
        "id": go_id,
        "description": description,
        "count": 10,
        "type": "GeneOntology",
    }
    group = {
        "id": "763192at7742",
        "name": "BRCA1",
        "level_name": "Vertebrata",
        "tax_id": 7742,
        "biological_process": [go(f"GO:{i:07d}", f"process-{i}") for i in range(21)],
        "cellular_component": [go("GO:9999999", "nucleus")],
        "unclassified GO terms": [go("GO:0000000", None), go("GO:9999999", None)],
        "interpro_domains": [
            {"id": f"IPR{i:06d}", "description": f"domain-{i}", "count": 5}
            for i in range(25)
        ],
        "ECnumber": [{"id": "2.3.2.27"}],
        "functional_category": [{"id": "T", "description": "signaling"}],
        "phyletic_profile": {"gene_count": 1020},
        "evolutionary_rate": 1.5,
        "gene_architecture": {"protein_median_length": 1758},
    }
    tool = OrthoDBTool({"fields": {"endpoint": "group"}})
    with patch(
        "tooluniverse.orthodb_tool.requests.get",
        return_value=_json_response({"data": group}),
    ):
        result = tool._get_group({"group_id": "763192at7742"})

    assert len(result["data"]["go_terms"]) == 22
    assert len(result["data"]["interpro_domains"]) == 25
    assert result["data"]["go_terms"][0]["category"] == "biological_process"
    assert result["data"]["phyletic_profile"]["gene_count"] == 1020
    assert result["metadata"]["annotation_counts"] == {
        "go_terms": 22,
        "kegg_pathways": 0,
        "interpro_domains": 25,
        "ec_numbers": 1,
        "functional_categories": 1,
    }


def test_fasta_structured_records_support_offset_and_exact_total():
    fasta = "\n".join(
        line
        for index in range(5)
        for line in (
            f'>{index}_0:gene{index} {{"pub_gene_id":"GENE{index}","organism_name":"Species {index}"}}',
            f"MSEQ{index}",
        )
    )
    response = MagicMock(text=fasta)
    response.raise_for_status.return_value = None
    tool = OrthoDBTool({"fields": {"endpoint": "fasta"}})
    with patch("tooluniverse.orthodb_tool.requests.get", return_value=response):
        result = tool._get_group_fasta(
            {"group_id": "group", "limit": 2, "offset": 2}
        )

    assert [row["pub_gene_id"] for row in result["data"]["sequences"]] == [
        "GENE2",
        "GENE3",
    ]
    assert result["data"]["total_sequences"] == 5
    assert result["data"]["next_offset"] == 4
    assert result["metadata"]["fasta_contains_all_sequences"] is True
