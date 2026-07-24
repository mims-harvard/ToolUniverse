"""Regression guard for Fix-R21C-2: PathoplexusCountTool's HTTP-error
messages told the caller to "check the organism slug" without ever naming
the actual valid slugs, forcing a trip back to the tool description.
Confirmed live for an unsupported organism (mycobacterium-tuberculosis):
the LAPIS API 404s with a generic body, and the tool's own error text
didn't help narrow down what a valid value looks like. Fixed by including
the known-organism list directly in the error message.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.pathoplexus_tool import PathoplexusCountTool, KNOWN_ORGANISMS

pytestmark = pytest.mark.unit


def _tool():
    return PathoplexusCountTool({"name": "pathoplexus_test", "fields": {"timeout": 30}})


def test_404_error_lists_known_organisms():
    tool = _tool()
    r = MagicMock()
    r.status_code = 404
    err = requests.exceptions.HTTPError(response=r)
    r.raise_for_status = MagicMock(side_effect=err)

    with patch("tooluniverse.pathoplexus_tool.requests.get", return_value=r):
        result = tool.run({"organism": "mycobacterium-tuberculosis"})

    assert result["status"] == "error"
    for organism in KNOWN_ORGANISMS:
        assert organism in result["error"]


def test_valid_organism_unaffected():
    tool = _tool()
    r = MagicMock()
    r.status_code = 200
    r.raise_for_status = MagicMock()
    r.json.return_value = {"data": [{"count": 42}]}

    with patch("tooluniverse.pathoplexus_tool.requests.get", return_value=r):
        result = tool.run({"organism": "west-nile"})

    assert result["status"] == "success"
