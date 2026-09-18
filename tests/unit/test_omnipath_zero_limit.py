"""OmniPath must forward limit=0 instead of dropping the parameter."""

from unittest.mock import patch

import pytest

from tooluniverse.omnipath_tool import OmniPathTool

pytestmark = pytest.mark.unit


def test_ligand_receptor_sends_zero_limit():
    tool = OmniPathTool(
        {
            "name": "omnipath_ligand_receptor",
            "fields": {"endpoint": "ligand_receptor"},
        }
    )
    captured = {}

    def fake_request(path, params):
        captured["path"] = path
        captured["params"] = params
        return []

    with patch.object(tool, "_make_request", side_effect=fake_request):
        result = tool.run({"partners": "TGFB1", "limit": 0})

    assert captured["params"]["limit"] == "0"
    assert result["status"] == "success"
    assert result["data"] == []
    assert result["metadata"]["total_interactions"] == 0
