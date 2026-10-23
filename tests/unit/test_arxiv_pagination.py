from unittest.mock import MagicMock, patch

from tooluniverse.arxiv_tool import ArXivTool


def _tool():
    return ArXivTool(
        {
            "name": "ArXiv_search_papers",
            "type": "ArXivTool",
            "parameter": {"type": "object", "properties": {}, "required": []},
        }
    )


def test_start_is_forwarded_to_arxiv_api():
    response = MagicMock(status_code=200)
    response.text = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<feed xmlns="http://www.w3.org/2005/Atom" '
        'xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">'
        "<opensearch:totalResults>10</opensearch:totalResults>"
        "<opensearch:startIndex>6</opensearch:startIndex>"
        "<opensearch:itemsPerPage>3</opensearch:itemsPerPage>"
        "</feed>"
    )

    tool = _tool()
    with (
        patch.object(tool, "_respect_rate_limit"),
        patch(
            "tooluniverse.arxiv_tool.request_with_retry", return_value=response
        ) as request,
    ):
        result = tool.run({"query": "CRISPR", "limit": 3, "start": 6})

    assert result["status"] == "success"
    assert result["metadata"]["total_results"] == 10
    assert result["metadata"]["start"] == 6
    assert result["metadata"]["pagination_stalled"] is True
    assert request.call_args.kwargs["params"]["start"] == 6
    assert request.call_args.kwargs["params"]["max_results"] == 3


def test_negative_start_is_rejected_instead_of_silently_clamped():
    tool = _tool()
    with patch("tooluniverse.arxiv_tool.request_with_retry") as request:
        result = tool.run({"query": "CRISPR", "start": -5})

    assert result["status"] == "error"
    request.assert_not_called()


def test_date_filter_does_not_overwrite_numeric_start():
    response = MagicMock(status_code=200)
    response.text = '<feed xmlns="http://www.w3.org/2005/Atom"></feed>'
    tool = _tool()
    with (
        patch.object(tool, "_respect_rate_limit"),
        patch(
            "tooluniverse.arxiv_tool.request_with_retry", return_value=response
        ) as request,
    ):
        tool.run(
            {
                "query": "CRISPR",
                "limit": 3,
                "start": 6,
                "date_from": "2024-01-01",
                "date_to": "2024-12-31",
            }
        )

    params = request.call_args.kwargs["params"]
    assert params["start"] == 6
    assert "submittedDate:[20240101000000 TO 20241231235959]" in params["search_query"]
