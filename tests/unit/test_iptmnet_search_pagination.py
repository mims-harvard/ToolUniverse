from unittest.mock import Mock

from tooluniverse.iptmnet_tool import iPTMnetTool


def test_search_has_offset_pagination():
    response = Mock(status_code=200)
    response.json.return_value = [
        {"iptm_id": f"P{i}", "organism": {"species": "human"}} for i in range(5)
    ]
    tool = iPTMnetTool({})
    tool.session.get = Mock(return_value=response)

    result = tool.run(
        {
            "operation": "search",
            "search_term": "kinase",
            "max_results": 2,
            "offset": 2,
        }
    )

    assert [row["uniprot_id"] for row in result["data"]] == ["P2", "P3"]
    assert result["metadata"]["total_results"] == 5
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_offset"] == 4
