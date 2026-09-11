"""A zero result limit must not return or fetch guideline records."""

from unittest.mock import patch

import pytest

from tooluniverse.unified_guideline_tools import OpenAlexGuidelinesTool

pytestmark = pytest.mark.unit


def test_zero_limit_returns_an_empty_guideline_envelope_without_a_request():
    tool = OpenAlexGuidelinesTool({"name": "OpenAlex_Guidelines_Search"})

    with patch("tooluniverse.unified_guideline_tools.requests.get") as get:
        result = tool.run({"query": "sepsis", "limit": 0})

    get.assert_not_called()
    assert result["status"] == "success"
    assert result["data"] == []
    assert result["metadata"]["returned"] == 0
