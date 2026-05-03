#!/usr/bin/env python3
"""
Contract-style tests to ensure literature tools return meaningful, consistent
shapes on basic validation failures (e.g., missing query).
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.europe_pmc_tool import EuropePMCTool
from tooluniverse.pmc_tool import PMCTool
from tooluniverse.semantic_scholar_tool import SemanticScholarTool


@pytest.mark.unit
@pytest.mark.parametrize(
    "tool_cls,args",
    [
        (EuropePMCTool, {"limit": 1}),
        (SemanticScholarTool, {"limit": 1}),
        (PMCTool, {"limit": 1}),
    ],
)
def test_missing_query_returns_list_with_error_item(tool_cls, args):
    tool = tool_cls({"name": "x"})
    result = tool.run(args)

    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], dict)
    assert "error" in result[0]
    assert result[0].get("retryable") is False
