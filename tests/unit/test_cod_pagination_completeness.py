"""Round 222: COD ignored pagination and structure-identity regression guards."""

import inspect
import json
from unittest.mock import patch

import pytest
from jsonschema import validate

from tooluniverse.base_rest_tool import BaseRESTTool
from tooluniverse.cod_tool import CODTool

pytestmark = pytest.mark.unit


def _config(name):
    with open("src/tooluniverse/data/cod_crystal_tools.json") as handle:
        return next(item for item in json.load(handle) if item["name"] == name)


def _records(count=5):
    return [
        {"file": str(1515581 + index), "formula": "- C9 H8 O4 -", "extra": index}
        for index in range(count)
    ]


def test_search_exposes_exact_total_and_reachable_next_page():
    """Every full-response COD record must remain reachable through offset."""
    upstream = {"status": "success", "data": _records(), "url": "https://cod/result"}
    with patch.object(BaseRESTTool, "run", return_value=upstream.copy()) as parent:
        first = CODTool(_config("COD_search_structures")).run(
            {"text": "aspirin", "limit": 2, "offset": 0}
        )
    with patch.object(BaseRESTTool, "run", return_value=upstream.copy()):
        second = CODTool(_config("COD_search_structures")).run(
            {"text": "aspirin", "limit": 2, "offset": 2}
        )

    assert [item["file"] for item in first["data"]] == ["1515581", "1515582"]
    assert [item["file"] for item in second["data"]] == ["1515583", "1515584"]
    assert first["metadata"]["total_results"] == 5
    assert first["metadata"]["next_offset"] == 2
    assert first["metadata"]["has_more"] is True
    assert first["metadata"]["upstream_pagination_supported"] is False
    assert parent.call_args.args[0] == {"text": "aspirin"}
    validate(first["data"], _config("COD_search_structures")["return_schema"])


@pytest.mark.parametrize(
    "arguments,error_fragment",
    [
        ({"text": "aspirin", "limit": True}, "limit"),
        ({"text": "aspirin", "limit": 0}, "limit"),
        ({"text": "aspirin", "offset": -1}, "offset"),
        ({"text": "aspirin", "offest": 2}, "offest"),
        ({"limit": 2}, "filter"),
        ({"query": "aspirin", "text": "quartz"}, "Conflicting"),
        ({"text": "aspirin", "results": 2, "limit": 3}, "Conflicting"),
    ],
)
def test_search_rejects_silent_broadening_and_invalid_pagination(
    arguments, error_fragment
):
    """Typos, conflicts, empty searches and invalid pages must fail before HTTP."""
    with patch.object(BaseRESTTool, "run") as parent:
        result = CODTool(_config("COD_search_structures")).run(arguments)
    assert result["status"] == "error"
    assert error_fragment.lower() in result["error"].lower()
    parent.assert_not_called()


def test_legacy_limit_aliases_remain_compatible_when_equal():
    """Equal results/max_results values map to one canonical local page size."""
    upstream = {"status": "success", "data": _records(), "url": "https://cod/result"}
    with patch.object(BaseRESTTool, "run", return_value=upstream):
        result = CODTool(_config("COD_search_structures")).run(
            {"query": "aspirin", "results": 2, "max_results": 2}
        )
    assert len(result["data"]) == 2
    assert result["metadata"]["limit"] == 2
    assert result["metadata"]["filters_applied"] == {"text": "aspirin"}


@pytest.mark.parametrize("arguments", [{}, {"id": "abc"}, {"id": 1515581}])
def test_get_structure_requires_seven_digit_string_id(arguments):
    """Missing or malformed IDs cannot accidentally request the full database."""
    with patch.object(BaseRESTTool, "run") as parent:
        result = CODTool(_config("COD_get_structure")).run(arguments)
    assert result["status"] == "error"
    parent.assert_not_called()


def test_get_structure_verifies_identity_and_preserves_full_record():
    """The requested ID must match while unknown upstream fields remain intact."""
    record = {
        "file": "1515581",
        "formula": "- C9 H8 O4 -",
        "extra_upstream_field": {"preserved": True},
    }
    with patch.object(
        BaseRESTTool,
        "run",
        return_value={
            "status": "success",
            "data": [record],
            "url": "https://cod/result",
        },
    ):
        result = CODTool(_config("COD_get_structure")).run({"cod_id": "1515581"})
    assert result["status"] == "success"
    assert result["data"][0]["extra_upstream_field"] == {"preserved": True}
    assert result["metadata"]["identity_verified"] is True
    assert result["metadata"]["source_record_complete"] is True
    validate(result["data"], _config("COD_get_structure")["return_schema"])


def test_get_structure_rejects_wrong_or_missing_payload_identity():
    """Empty and mismatched upstream payloads cannot be presented as the requested ID."""
    tool = CODTool(_config("COD_get_structure"))
    with patch.object(
        BaseRESTTool, "run", return_value={"status": "success", "data": []}
    ):
        missing = tool.run({"id": "1515581"})
    with patch.object(
        BaseRESTTool,
        "run",
        return_value={"status": "success", "data": [{"file": "1515582"}]},
    ):
        mismatch = tool.run({"id": "1515581"})
    assert missing["status"] == "error" and "not found" in missing["error"]
    assert mismatch["status"] == "error" and "identity" in mismatch["error"]


def test_config_and_generated_wrapper_publish_offset_controls():
    """Agents must be able to request every reachable local COD page."""
    properties = _config("COD_search_structures")["parameter"]["properties"]
    # `limit` deliberately carries no schema default: the generated wrapper
    # sends every defaulted parameter, and an injected limit=100 collided with
    # the max_results/results aliases ("Conflicting values for max_results and
    # limit"), making the SDK entry point unusable.  The effective default is
    # documented instead and applied by the tool when limit is absent.
    assert "default" not in properties["limit"]
    assert "100" in properties["limit"]["description"]
    assert properties["offset"]["default"] == 0

    from tooluniverse.tools.COD_search_structures import COD_search_structures

    parameters = inspect.signature(COD_search_structures).parameters
    assert "limit" in parameters and "offset" in parameters
    assert parameters["limit"].default is None
    assert parameters["offset"].default == 0
