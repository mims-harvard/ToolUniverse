"""Regression guard for Fix-R77A-1: iCite_get_publications double-wrapped its
response.

iCite_get_publications is a plain BaseRESTTool hitting the raw iCite API
(https://icite.od.nih.gov/api/pubs) directly. The raw API's own JSON body is
already shaped {"data": [...], ...}. Without fields.extract_path configured,
BaseRESTTool._process_response wrapped that whole raw body under another
top-level "data" key, producing {"data": {"data": [...], ...}} -- violating
the declared return_schema, which requires "data" to be a bare array of
publication objects.
"""

import json
from unittest.mock import MagicMock

import jsonschema
import pytest

from tooluniverse.base_rest_tool import BaseRESTTool

pytestmark = pytest.mark.unit


def _load_tool_config():
    with open("src/tooluniverse/data/icite_tools.json") as f:
        tools = json.load(f)
    return next(t for t in tools if t["name"] == "iCite_get_publications")


def _mock_response(payload):
    resp = MagicMock()
    resp.json.return_value = payload
    resp.headers = {"content-type": "application/json"}
    return resp


def test_config_declares_extract_path():
    config = _load_tool_config()
    assert config["fields"].get("extract_path") == "data"


def test_process_response_unwraps_raw_data_key():
    config = _load_tool_config()
    tool = BaseRESTTool(config)

    raw_icite_body = {
        "data": [
            {"pmid": 24453148, "citation_count": 4},
            {"pmid": 24453150, "citation_count": 5},
        ],
        "meta": {"count": 2},
    }
    result = tool._process_response(_mock_response(raw_icite_body), "https://icite.od.nih.gov/api/pubs")

    assert result["data"] == raw_icite_body["data"]
    assert isinstance(result["data"], list)


def test_unwrapped_response_satisfies_return_schema():
    config = _load_tool_config()
    tool = BaseRESTTool(config)

    raw_icite_body = {
        "data": [{"pmid": 24453148, "citation_count": 4, "title": "t"}],
        "meta": {"count": 1},
    }
    result = tool._process_response(_mock_response(raw_icite_body), "https://icite.od.nih.gov/api/pubs")

    jsonschema.validate(instance=result, schema=config["return_schema"])


def test_without_extract_path_would_double_wrap():
    """Sanity check that the bug shape is real: dropping extract_path
    reproduces the pre-fix double-wrap so the schema validation fails."""
    config = _load_tool_config()
    broken_config = json.loads(json.dumps(config))
    del broken_config["fields"]["extract_path"]
    tool = BaseRESTTool(broken_config)

    raw_icite_body = {"data": [{"pmid": 1}], "meta": {"count": 1}}
    result = tool._process_response(_mock_response(raw_icite_body), "https://icite.od.nih.gov/api/pubs")

    assert result["data"] == raw_icite_body  # double-wrapped, not unwrapped
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=result, schema=config["return_schema"])
