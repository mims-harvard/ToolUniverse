from unittest.mock import MagicMock, patch

from tooluniverse.datagov_tool import DataGovTool


def _response(payload):
    response = MagicMock()
    response.json.return_value = payload
    return response


def test_cursor_and_all_distributions_are_preserved():
    distributions = [
        {"title": f"file-{i}", "downloadURL": f"https://example.org/{i}.csv"}
        for i in range(27)
    ]
    body = {
        "after": "next-cursor",
        "results": [
            {
                "title": "Form N-PORT Data Sets",
                "slug": "n-port",
                "dcat": {"distribution": distributions},
            }
        ],
    }
    tool = DataGovTool({"name": "DataGov_search_datasets"})

    with patch(
        "tooluniverse.datagov_tool.requests.get", return_value=_response(body)
    ) as get:
        result = tool.run({"query": "climate", "rows": 3, "after": "cursor-1"})

    assert get.call_args.kwargs["params"] == {
        "q": "climate",
        "_format": "json",
        "per_page": 3,
        "after": "cursor-1",
    }
    data = result["data"]
    assert data["total_count"] is None
    assert data["returned"] == 1
    assert data["next_after"] == "next-cursor"
    assert data["has_more"] is True
    assert data["page_size"] == 3
    assert data["datasets"][0]["resource_count"] == 27
    assert len(data["datasets"][0]["resources"]) == 27
