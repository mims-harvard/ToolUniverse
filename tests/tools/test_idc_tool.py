"""
Unit tests for the NCI Image Data Commons (IDC) v3 API tool.

IDC requires no API key, so these tests mock the HTTP layer for
determinism (matching the pattern used elsewhere in this repo) rather
than depending on network access during CI.
"""

import json
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def tool_config():
    with open("src/tooluniverse/data/idc_tools.json") as f:
        tools = json.load(f)
    return next(t for t in tools if t["name"] == "IDC_list_collections")


@pytest.fixture
def get_collection_config():
    with open("src/tooluniverse/data/idc_tools.json") as f:
        tools = json.load(f)
    return next(t for t in tools if t["name"] == "IDC_get_collection")


@pytest.fixture
def cohort_counts_config():
    with open("src/tooluniverse/data/idc_tools.json") as f:
        tools = json.load(f)
    return next(t for t in tools if t["name"] == "IDC_get_cohort_counts")


def _ok_response(body):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = body
    resp.raise_for_status.return_value = None
    return resp


def _status_response(status_code, text=""):
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    resp.json.return_value = {}
    resp.raise_for_status.return_value = None
    return resp


class TestMissingOperation:
    def test_missing_operation_is_an_error(self, tool_config):
        from tooluniverse.idc_tool import IDCTool

        tool = IDCTool(tool_config)
        result = tool.run({})
        assert result["status"] == "error"
        assert "operation" in result["error"]

    def test_unknown_operation_is_an_error(self, tool_config):
        from tooluniverse.idc_tool import IDCTool

        tool = IDCTool(tool_config)
        result = tool.run({"operation": "not_real"})
        assert result["status"] == "error"
        assert "Unknown operation" in result["error"]


class TestListCollections:
    def test_successful_list(self, tool_config):
        from tooluniverse.idc_tool import IDCTool

        tool = IDCTool(tool_config)
        body = [{"collection_id": "4d_lung", "collection_name": "4D-Lung"}]
        with patch("requests.get", return_value=_ok_response(body)):
            result = tool.run({"operation": "list_collections"})
        assert result["status"] == "success"
        assert result["data"]["total_count"] == 1
        assert result["data"]["collections"][0]["collection_id"] == "4d_lung"


class TestGetCollection:
    def test_missing_collection_id_is_an_error(self, get_collection_config):
        from tooluniverse.idc_tool import IDCTool

        tool = IDCTool(get_collection_config)
        result = tool.run({"operation": "get_collection"})
        assert result["status"] == "error"
        assert "collection_id" in result["error"]

    def test_unknown_collection_returns_clean_error(self, get_collection_config):
        from tooluniverse.idc_tool import IDCTool

        tool = IDCTool(get_collection_config)
        with patch("requests.get", return_value=_status_response(422)):
            result = tool.run(
                {"operation": "get_collection", "collection_id": "not_a_real_id"}
            )
        assert result["status"] == "error"
        assert "not found" in result["error"].lower()

    def test_successful_get_returns_detail(self, get_collection_config):
        from tooluniverse.idc_tool import IDCTool

        tool = IDCTool(get_collection_config)
        body = {"collection_id": "4d_lung", "patients": 20, "modalities": ["CT"]}
        with patch("requests.get", return_value=_ok_response(body)):
            result = tool.run(
                {"operation": "get_collection", "collection_id": "4d_lung"}
            )
        assert result["status"] == "success"
        assert result["data"]["patients"] == 20


class TestCohortCounts:
    def test_bad_filter_returns_clean_error(self, cohort_counts_config):
        from tooluniverse.idc_tool import IDCTool

        tool = IDCTool(cohort_counts_config)
        with patch(
            "requests.post", return_value=_status_response(400, "bad filter")
        ):
            result = tool.run(
                {"operation": "get_cohort_counts", "terms": {"BadAttr": ["x"]}}
            )
        assert result["status"] == "error"
        assert "filter" in result["error"].lower()

    def test_successful_counts(self, cohort_counts_config):
        from tooluniverse.idc_tool import IDCTool

        tool = IDCTool(cohort_counts_config)
        body = {
            "patients": 22645,
            "studies": 22730,
            "series": 76299,
            "instances": 391932,
            "size_TB": 49.02,
            "filters_applied": {"terms": {"Modality": ["SM"]}, "ranges": {}},
            "warnings": [],
        }
        with patch("requests.post", return_value=_ok_response(body)):
            result = tool.run(
                {"operation": "get_cohort_counts", "terms": {"Modality": ["SM"]}}
            )
        assert result["status"] == "success"
        assert result["data"]["series"] == 76299

    def test_empty_filter_is_allowed(self, cohort_counts_config):
        from tooluniverse.idc_tool import IDCTool

        tool = IDCTool(cohort_counts_config)
        body = {
            "patients": 85362,
            "studies": 166740,
            "series": 1032911,
            "instances": 57409445,
            "size_TB": 99.267,
            "filters_applied": {"terms": {}, "ranges": {}},
            "warnings": ["No filter predicates were applied"],
        }
        with patch("requests.post", return_value=_ok_response(body)):
            result = tool.run({"operation": "get_cohort_counts"})
        assert result["status"] == "success"
        assert result["data"]["warnings"]
