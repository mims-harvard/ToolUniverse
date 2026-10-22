from unittest.mock import Mock

from tooluniverse.wikipedia_tool import WikipediaContentTool


def test_content_forwards_link_continuation_and_reports_next_token(monkeypatch) -> None:
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "continue": {"plcontinue": "2146034|0|CAS9", "continue": "||"},
        "query": {
            "pages": {
                "2146034": {
                    "title": "CRISPR",
                    "fullurl": "https://en.wikipedia.org/wiki/CRISPR",
                    "extract": "CRISPR summary",
                    "links": [{"title": "Cas12"}, {"title": "Cas13"}],
                }
            }
        },
    }
    get = Mock(return_value=response)
    monkeypatch.setattr("tooluniverse.wikipedia_tool.requests.get", get)
    tool = WikipediaContentTool({})

    result = tool.run(
        {
            "title": "CRISPR",
            "link_limit": 2,
            "links_continue": "2146034|0|CAS12",
        }
    )

    params = get.call_args.kwargs["params"]
    assert params["pllimit"] == 2
    assert params["plcontinue"] == "2146034|0|CAS12"
    assert result["links"] == ["Cas12", "Cas13"]
    assert result["links_returned"] == 2
    assert result["links_has_more"] is True
    assert result["next_links_continue"] == "2146034|0|CAS9"
