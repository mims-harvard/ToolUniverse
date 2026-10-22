from unittest.mock import Mock, patch

from tooluniverse.base_rest_tool import BaseRESTTool
from tooluniverse.europe_pmc_tool import EuropePMCRESTTool


def base_config(kind="citations"):
    container, record = (
        ("citationList", "citation")
        if kind == "citations"
        else ("referenceList", "reference")
    )
    return {
        "name": f"EPMC_get_{kind}",
        "type": "BaseRESTTool",
        "parameter": {
            "properties": {
                "pmid": {"type": "string"},
                "page": {"type": "integer", "default": 1},
                "pageSize": {"type": "integer", "default": 25},
            }
        },
        "fields": {
            "endpoint": (
                "https://example.test/MED/{pmid}/"
                f"{kind}?format=json&page={{page}}&pageSize={{pageSize}}"
            ),
            "pagination": "epmc_page",
            "record_container": container,
            "record_key": record,
        },
    }


def custom_config(kind="references"):
    container, record = (
        ("citationList", "citation")
        if kind == "citations"
        else ("referenceList", "reference")
    )
    return {
        "name": f"EuropePMC_get_{kind}",
        "type": "EuropePMCRESTTool",
        "parameter": {
            "properties": {
                "source": {"type": "string", "default": "MED"},
                "article_id": {"type": "string"},
                "page": {"type": "integer", "default": 1},
                "page_size": {"type": "integer", "default": 25},
            }
        },
        "fields": {
            "endpoint": f"https://example.test/{{source}}/{{article_id}}/{kind}",
            "pagination": "epmc_page",
            "record_container": container,
            "record_key": record,
        },
    }


def response(payload):
    result = Mock(status_code=200, text="", url="https://example.test/request")
    result.json.return_value = payload
    return result


def test_base_epmc_citations_exposes_exact_page_metadata():
    payload = {
        "hitCount": 8,
        "citationList": {"citation": [{"id": "a"}, {"id": "b"}, {"id": "c"}]},
    }
    tool = BaseRESTTool(base_config())
    with patch(
        "tooluniverse.base_rest_tool.request_with_retry",
        return_value=response(payload),
    ):
        result = tool.run({"pmid": "25378148", "page": 2, "pageSize": 3})

    assert result["count"] == 3
    assert result["metadata"] == {
        "returned": 3,
        "total_results": 8,
        "total_results_is_exact": True,
        "page": 2,
        "page_size": 3,
        "total_pages": 3,
        "has_more": True,
        "next_page": 3,
        "truncated": True,
        "result_set_complete": False,
        "record_path": "citationList.citation",
        "pagination_scope": "europe_pmc_hitcount_one_based_page",
    }


def test_custom_epmc_references_exposes_last_page_metadata_and_page_size():
    payload = {
        "hitCount": 8,
        "referenceList": {"reference": [{"id": "g"}, {"id": "h"}]},
    }
    tool = EuropePMCRESTTool(custom_config())
    with patch(
        "tooluniverse.europe_pmc_tool.request_with_retry",
        return_value=response(payload),
    ) as request:
        result = tool.run(
            {"source": "MED", "article_id": "25378148", "page": 3, "page_size": 3}
        )

    assert result["count"] == 2
    assert result["metadata"]["total_results"] == 8
    assert result["metadata"]["total_pages"] == 3
    assert result["metadata"]["has_more"] is False
    assert result["metadata"]["next_page"] is None
    assert result["metadata"]["record_path"] == "referenceList.reference"
    assert request.call_args.kwargs["params"]["pageSize"] == 3
    assert request.call_args.kwargs["params"]["page"] == 3


def test_both_epmc_implementations_reject_silent_empty_coercions_without_network():
    base = BaseRESTTool(base_config())
    custom = EuropePMCRESTTool(custom_config())
    with patch("tooluniverse.base_rest_tool.request_with_retry") as base_request:
        assert base.run({"pmid": "x", "page": 0})["parameter"] == "page"
        assert base.run({"pmid": "x", "pageSize": 0})["parameter"] == "pageSize"
        assert base.run({"pmid": "x", "pageSize": 1001})["parameter"] == "pageSize"
        assert base.run({"pmid": "x", "page": True})["parameter"] == "page"
    base_request.assert_not_called()

    with patch("tooluniverse.europe_pmc_tool.request_with_retry") as custom_request:
        assert custom.run({"article_id": "x", "page": 0})["parameter"] == "page"
        assert custom.run({"article_id": "x", "page_size": 0})["parameter"] == "page_size"
        assert custom.run({"article_id": "x", "page_size": 1001})["parameter"] == "page_size"
        assert custom.run({"article_id": "x", "page": True})["parameter"] == "page"
    custom_request.assert_not_called()
