"""Unit test: civic_search_molecular_profiles must not silently drop unknown params.

Regression: civic_search_molecular_profiles only filters by query/name + limit
(the GraphQL query binds nothing else). Passing a very natural param like
variant_id ("profiles for CIViC variant 78") was silently ignored, returning the
full unfiltered profile list (BRAF V600E, ERBB2 Amplification, ...) as a
plausible-but-wrong "success". The tool now rejects unrecognized params with an
actionable hint, mirroring civic_search_evidence_items.
"""
import glob
import json
from unittest.mock import patch

import pytest

from tooluniverse.civic_tool import CIViCTool


def _load(name):
    for f in glob.glob("src/tooluniverse/data/*.json"):
        try:
            data = json.load(open(f))
        except ValueError:
            continue
        if isinstance(data, list):
            for tool in data:
                if isinstance(tool, dict) and tool.get("name") == name:
                    return tool
    raise AssertionError(f"tool config not found: {name}")


def _tool():
    return CIViCTool(_load("civic_search_molecular_profiles"))


@pytest.mark.unit
def test_unknown_param_rejected_with_hint():
    result = _tool().run({"variant_id": 78})
    assert result["status"] == "error"
    assert "variant_id" in result["error"]
    # Points the user at the right approach instead of silently dumping.
    assert "civic_get_variant" in result["error"]


@pytest.mark.unit
def test_valid_query_param_passes_guard():
    """A supported param set must NOT trip the guard (it proceeds to the API)."""

    class _Resp:
        status_code = 200

        def json(self):
            return {"data": {"molecularProfiles": {"nodes": []}}}

        def raise_for_status(self):
            pass

    with patch("tooluniverse.civic_tool.requests.post", return_value=_Resp()):
        result = _tool().run({"query": "KRAS G12C", "limit": 5})
    # Not the guard's rejection error.
    assert not (
        result.get("status") == "error"
        and "Unrecognized parameter" in result.get("error", "")
    )
