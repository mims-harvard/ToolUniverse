from unittest.mock import Mock, patch

from tooluniverse.osf_preprints_tool import OSFPreprintsTool


def tool():
    return OSFPreprintsTool({"name": "OSF_search_preprints"})


def response(payload):
    result = Mock(
        status_code=200, text="", headers={"content-type": "application/json"}
    )
    result.json.return_value = payload
    result.raise_for_status.return_value = None
    return result


def payload():
    return {
        "data": [
            {
                "id": "mgyjv_v2",
                "attributes": {
                    "title": "Psychology study",
                    "description": "Abstract text",
                    "date_published": "2026-08-11T14:35:05Z",
                    "is_published": True,
                    "doi": None,
                },
                "links": {
                    "html": "https://osf.io/preprints/psyarxiv/mgyjv_v2/",
                    "preprint_doi": "https://doi.org/10.31234/osf.io/mgyjv_v2",
                },
                "relationships": {"provider": {"data": {"id": "psyarxiv"}}},
            }
        ],
        "links": {
            "next": "https://api.osf.io/v2/preprints/?page=3&page%5Bsize%5D=1",
            "meta": {"total": 1279, "per_page": 1},
        },
    }


def test_osf_uses_bare_page_and_exposes_exact_continuation():
    with patch(
        "tooluniverse.osf_preprints_tool.requests.get", return_value=response(payload())
    ) as request:
        result = tool().run(
            {
                "query": "psychology",
                "search_field": "title",
                "provider": "psyarxiv",
                "max_results": 1,
                "page": 2,
            }
        )

    params = request.call_args.kwargs["params"]
    assert params["page"] == 2
    assert "page[number]" not in params
    assert params["filter[title]"] == "psychology"
    assert params["filter[provider]"] == "psyarxiv"
    assert result["metadata"]["total_results"] == 1279
    assert result["metadata"]["total_pages"] == 1279
    assert result["metadata"]["next_page"] == 3
    assert result["data"][0]["doi"] == "10.31234/osf.io/mgyjv_v2"
    assert result["data"][0]["provider"] == "psyarxiv"


def test_osf_description_filter_is_explicit():
    body = payload()
    body["links"]["next"] = None
    body["links"]["meta"] = {"total": 1, "per_page": 10}
    with patch(
        "tooluniverse.osf_preprints_tool.requests.get", return_value=response(body)
    ) as request:
        result = tool().run(
            {"query": "psychology", "search_field": "description", "max_results": 10}
        )
    assert request.call_args.kwargs["params"]["filter[description]"] == "psychology"
    assert result["metadata"]["result_set_complete"] is True


def test_osf_rejects_values_upstream_silently_coerces():
    with patch("tooluniverse.osf_preprints_tool.requests.get") as request:
        assert (
            tool().run({"query": "x", "max_results": 101})["parameter"] == "max_results"
        )
        assert (
            tool().run({"query": "x", "max_results": True})["parameter"]
            == "max_results"
        )
        assert tool().run({"query": "x", "page": 0})["parameter"] == "page"
        assert (
            tool().run({"query": "x", "search_field": "both"})["parameter"]
            == "search_field"
        )
    request.assert_not_called()
