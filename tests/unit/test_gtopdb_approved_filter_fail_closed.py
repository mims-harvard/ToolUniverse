"""Round 224: GtoPdb approved_only must be exposed, exact, and fail closed."""

import inspect
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.gtopdb_tool import GtoPdbRESTTool
from tooluniverse.tools.GtoPdb_get_interactions import GtoPdb_get_interactions

pytestmark = pytest.mark.unit

CONFIG_PATH = (
    Path(__file__).parents[2] / "src" / "tooluniverse" / "data" / "gtopdb_tools.json"
)


def _config():
    configs = json.loads(CONFIG_PATH.read_text())
    return next(c for c in configs if c["name"] == "GtoPdb_get_interactions")


def _response(payload, status=200):
    response = MagicMock()
    response.status_code = status
    response.json.return_value = payload
    response.text = ""
    return response


def test_approved_filter_cross_references_before_pagination():
    """Only ligand IDs explicitly marked approved may survive the filter."""
    interactions = [
        {"interactionId": 1, "targetId": 1797, "ligandId": 10},
        {"interactionId": 2, "targetId": 1797, "ligandId": 20},
        {"interactionId": 3, "targetId": 1797, "ligandId": 30},
        {"interactionId": 4, "targetId": 1797, "ligandId": 40},
    ]
    registry = [
        {"ligandId": 10, "approved": True},
        {"ligandId": 20, "approved": False},
        {"ligandId": 30, "approved": True},
    ]
    with patch(
        "tooluniverse.gtopdb_tool.request_with_retry",
        side_effect=[_response(interactions), _response(registry)],
    ) as request:
        result = GtoPdbRESTTool(_config()).run(
            {"targetId": 1797, "approved_only": True, "limit": 1, "offset": 1}
        )

    assert result["status"] == "success"
    assert [row["interactionId"] for row in result["data"]] == [3]
    assert result["approved_only_applied"] is True
    assert result["unfiltered_total_available"] == 4
    assert result["total_available"] == 2
    assert result["offset"] == 1
    assert request.call_count == 2
    assert request.call_args_list[1].args[2].endswith("/ligands?approved=true")
    assert "approved drugs for this target are not represented" not in result["coverage_note"]


@pytest.mark.parametrize(
    "approved_response",
    [
        _response([], status=503),
        _response({"unexpected": "object"}),
    ],
)
def test_approved_filter_failure_never_returns_unfiltered_success(approved_response):
    """Unavailable or malformed registry data must fail closed."""
    interactions = [{"interactionId": 1, "targetId": 1797, "ligandId": 20}]
    with patch(
        "tooluniverse.gtopdb_tool.request_with_retry",
        side_effect=[_response(interactions), approved_response],
    ):
        result = GtoPdbRESTTool(_config()).run(
            {"targetId": 1797, "approved_only": True}
        )

    assert result["status"] == "error"
    assert result["filter"] == "approved_only"
    assert result["filter_applied"] is False
    assert "unfiltered interactions were not returned" in result["error"]
    assert "data" not in result


def test_invalid_approved_filter_fails_before_network():
    """Truth-like strings cannot silently enable or disable the filter."""
    with patch("tooluniverse.gtopdb_tool.request_with_retry") as request:
        result = GtoPdbRESTTool(_config()).run(
            {"targetId": 1797, "approved_only": "true"}
        )
    assert result["status"] == "error"
    assert "boolean" in result["error"]
    request.assert_not_called()


def test_config_and_generated_wrapper_expose_approved_filter():
    """Agents must be able to request the implemented filter through public schemas."""
    config = _config()
    approved = config["parameter"]["properties"]["approved_only"]
    assert approved["type"] == "boolean"
    assert approved["default"] is False
    assert "fail" in config["description"].lower()
    parameters = inspect.signature(GtoPdb_get_interactions).parameters
    assert parameters["approved_only"].default is False
    success_schema = config["return_schema"]["oneOf"][0]
    assert success_schema["type"] == "object"
    assert "approved_only_applied" in success_schema["properties"]
