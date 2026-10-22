import json
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from tooluniverse.base_rest_tool import BaseRESTTool
from tooluniverse.dailymed_tool import SearchSPLTool
from tooluniverse.tools.DailyMed_search_spls import DailyMed_search_spls


ROOT = Path(__file__).resolve().parents[2]


def drug_class_config():
    configs = json.loads(
        (ROOT / "src/tooluniverse/data/clinical_guidelines_tools.json").read_text()
    )
    return next(c for c in configs if c["name"] == "DailyMed_search_drug_classes")


def dailymed_response(*, total=136, page=1, pagesize=3, names=None):
    names = names or ["A", "B", "C"]
    response = Mock(status_code=200)
    response.json.return_value = {
        "data": [{"name": name} for name in names],
        "metadata": {
            "elements_per_page": pagesize,
            "current_url": "https://example.test/current",
            "next_page_url": (
                "https://example.test/next" if page * pagesize < total else "null"
            ),
            "total_elements": total,
            "total_pages": (total + pagesize - 1) // pagesize,
            "current_page": page,
            "previous_page": page - 1 if page > 1 else "null",
            "previous_page_url": "https://example.test/prev" if page > 1 else "null",
            "next_page": page + 1 if page * pagesize < total else "null",
        },
    }
    return response


def test_drug_class_search_exposes_exact_continuation_and_normalizes_nulls():
    tool = BaseRESTTool(drug_class_config())
    with patch(
        "tooluniverse.base_rest_tool.request_with_retry",
        return_value=dailymed_response(),
    ) as request:
        result = tool.run({"drug_class_name": "anti", "pagesize": 3, "page": 1})

    assert result["status"] == "success"
    assert result["metadata"]["returned"] == 3
    assert result["metadata"]["total_results"] == 136
    assert result["metadata"]["total_pages"] == 46
    assert result["metadata"]["next_page"] == 2
    assert result["data"]["metadata"]["previous_page"] is None
    assert result["data"]["metadata"]["previous_page_url"] is None
    assert request.call_args.kwargs["params"] == {
        "drug_class_name": "anti",
        "pagesize": 3,
        "page": 1,
    }


def test_drug_class_search_rejects_upstream_coercions():
    tool = BaseRESTTool(drug_class_config())
    with patch("tooluniverse.base_rest_tool.request_with_retry") as request:
        assert tool.run({"drug_class_name": "anti", "page": 0})["parameter"] == "page"
        assert (
            tool.run({"drug_class_name": "anti", "pagesize": 101})["parameter"]
            == "pagesize"
        )
        assert (
            tool.run({"drug_class_name": "anti", "pagesize": True})["parameter"]
            == "pagesize"
        )
    request.assert_not_called()


def test_spl_search_accepts_rxcui_only_and_exposes_exact_metadata():
    tool = SearchSPLTool({"name": "DailyMed_search_spls"})
    with patch(
        "tooluniverse.dailymed_tool.requests.get",
        return_value=dailymed_response(total=95),
    ) as request:
        result = tool.run({"rxcui": "197381", "pagesize": 3, "page": 1})

    assert result["status"] == "success"
    assert request.call_args.kwargs["params"]["rxcui"] == "197381"
    assert "drug_name" not in request.call_args.kwargs["params"]
    assert result["metadata"]["total_results"] == 95
    assert result["metadata"]["returned"] == 3
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_page"] == 2


def test_spl_search_requires_a_filter_and_validates_pagination():
    tool = SearchSPLTool({"name": "DailyMed_search_spls"})
    with patch("tooluniverse.dailymed_tool.requests.get") as request:
        assert tool.run({})["status"] == "error"
        assert tool.run({"drug_name": "aspirin", "page": 0})["parameter"] == "page"
        assert (
            tool.run({"drug_name": "aspirin", "pagesize": 101})["parameter"]
            == "pagesize"
        )
        assert (
            tool.run({"drug_name": "aspirin", "limit": False})["parameter"]
            == "pagesize"
        )
    request.assert_not_called()


def test_generated_spl_wrapper_can_omit_drug_name_for_rxcui_query():
    client = MagicMock()
    client.run_one_function.return_value = {"status": "success", "data": []}
    with patch(
        "tooluniverse.tools.DailyMed_search_spls.get_shared_client",
        return_value=client,
    ):
        DailyMed_search_spls(rxcui="197381", pagesize=3)

    arguments = client.run_one_function.call_args.args[0]["arguments"]
    assert arguments["rxcui"] == "197381"
    assert "drug_name" not in arguments
