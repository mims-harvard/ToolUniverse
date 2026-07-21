"""Round 84: ReMap_get_peaks_in_region accepted an inverted region
(start >= end, e.g. "chr1:1010000-1000000") as valid format and silently
forwarded it to the ReMap REST API, which returns HTTP 200 with zero peaks
for it -- indistinguishable from "this valid, modest region genuinely has no
ChIP-seq peaks." Fixed by validating start < end alongside the existing
chrom:start-end format check.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.remap_tool import ReMapRESTTool

pytestmark = pytest.mark.unit


def _tool():
    return ReMapRESTTool({"name": "ReMap_get_peaks_in_region", "fields": {}})


def test_inverted_region_rejected():
    tool = _tool()
    result = tool._get_peaks_in_region({"region": "chr1:1010000-1000000"})
    assert result["status"] == "error"
    assert "start must be less than end" in result["error"]


def test_zero_width_region_rejected():
    tool = _tool()
    result = tool._get_peaks_in_region({"region": "chr1:1000000-1000000"})
    assert result["status"] == "error"
    assert "start must be less than end" in result["error"]


def test_malformed_region_still_rejected():
    tool = _tool()
    result = tool._get_peaks_in_region({"region": "not-a-region"})
    assert result["status"] == "error"
    assert "Invalid region format" in result["error"]


def test_valid_region_still_reaches_the_api():
    tool = _tool()
    resp = MagicMock()
    resp.json.return_value = {"peaks": []}
    resp.raise_for_status.return_value = None
    with patch.object(tool.session, "get", return_value=resp) as get:
        result = tool._get_peaks_in_region({"region": "chr1:1000000-1010000"})
    assert result["status"] == "success"
    assert "chr1:1000000-1010000" in get.call_args.args[0]
