"""Regression guard: Reactome_query_by_ids advertised `species` and `types`
filters that could never work. The POST branch for /data/query/ids sends the
IDs as a plain-text body with no `params=`, so both arguments were dropped;
and Reactome's endpoint has no server-side filtering either -- a live probe
returned byte-identical payloads for species=Homo sapiens, species=9606,
species=Mus musculus, types=Reaction and species+types. Querying
["R-HSA-73817", "R-MMU-73817"] with species="Homo sapiens" returned the mouse
record too. Both filters are now rejected at input, scoped to this endpoint
only -- other Reactome tools take species as a genuine path parameter.

Offline: every assertion exercises the input-validation path, and the HTTP
transport is patched to fail loudly if it is ever reached.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tooluniverse.reactome_tool import ReactomeRESTTool

pytestmark = pytest.mark.unit

_CONFIG_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "tooluniverse"
    / "data"
    / "reactome_tools.json"
)
_IDS = ["R-HSA-73817", "R-MMU-73817"]


def _config(name):
    configs = json.loads(_CONFIG_PATH.read_text())
    return next(c for c in configs if c["name"] == name)


def _no_network(*args, **kwargs):
    raise AssertionError("HTTP request should not be made for a rejected argument")


@pytest.mark.parametrize(
    "extra",
    [
        {"species": "Homo sapiens"},
        {"species": "9606"},
        {"types": ["Reaction"]},
        {"species": "Homo sapiens", "types": ["Pathway"]},
    ],
)
def test_unsupported_filters_are_rejected_without_a_request(extra):
    tool = ReactomeRESTTool(_config("Reactome_query_by_ids"))
    with patch("tooluniverse.reactome_tool.request_with_retry", _no_network):
        result = tool.run({"ids": _IDS, **extra}, validate=False)
    assert result["status"] == "error"
    error = result["error"]
    for key in extra:
        assert repr(key) in error
    # The message must tell the caller how to get what they wanted.
    assert "speciesName" in error
    assert "schemaClass" in error
    assert "Reactome_list_top_pathways" in error


def test_query_by_ids_without_filters_still_reaches_the_endpoint():
    tool = ReactomeRESTTool(_config("Reactome_query_by_ids"))
    calls = {}

    def _capture(_session, method, url, **kwargs):
        calls["method"] = method
        calls["url"] = url
        calls["data"] = kwargs.get("data")
        raise RuntimeError("stop after transport is reached")

    with patch("tooluniverse.reactome_tool.request_with_retry", _capture):
        tool.run({"ids": _IDS}, validate=False)

    assert calls["method"] == "POST"
    assert calls["url"].endswith("/data/query/ids")
    assert calls["data"] == "R-HSA-73817,R-MMU-73817"


def test_species_path_parameter_tools_are_unaffected():
    tool = ReactomeRESTTool(_config("Reactome_list_top_pathways"))
    calls = {}

    def _capture(_session, method, url, **kwargs):
        calls["url"] = url
        raise RuntimeError("stop after transport is reached")

    with patch("tooluniverse.reactome_tool.request_with_retry", _capture):
        tool.run({"species": "Homo sapiens"}, validate=False)

    # species is a path parameter here, so it must still be honoured.
    assert "Homo sapiens" in calls["url"]


def test_config_no_longer_advertises_working_filters():
    props = _config("Reactome_query_by_ids")["parameter"]["properties"]
    for key in ("species", "types"):
        description = props[key]["description"]
        assert "NOT SUPPORTED" in description
        assert not description.startswith("Optional: Filter by")
