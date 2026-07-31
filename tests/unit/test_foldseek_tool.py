"""Regression guard for Fix-R2A-008: FoldseekTool's default search mode.

The JSON schema documents 'mode' defaulting to '3diaa' (Foldseek's fast
structural-alphabet search), but the Python code's own fallback was
'tmalign' whenever the caller omitted the parameter. This silently returned
noise-level hits (e-value ~0.3, ~2-5% identity) for every query, including
trivial control cases (e.g. hemoglobin 4HHB against pdb100).
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.foldseek_tool import FoldseekTool

pytestmark = pytest.mark.unit


def _tool():
    return FoldseekTool({"name": "Foldseek_search_structure", "fields": {"operation": "search"}})


def _resp(status_code=200, json_data=None, text=""):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_data or {}
    r.text = text
    return r


def test_default_mode_is_3diaa_not_tmalign():
    """The outgoing Foldseek ticket submission must use mode=3diaa when the
    caller doesn't specify one, matching the schema's documented default."""
    tool = _tool()

    pdb_file_resp = _resp(200, text="ATOM ...")
    ticket_resp = _resp(200, {"id": "ticket123"})
    status_resp = _resp(200, {"status": "COMPLETE"})
    result_resp = _resp(200, {"results": []})

    with patch("tooluniverse.foldseek_tool.requests.get") as mock_get, patch(
        "tooluniverse.foldseek_tool.requests.post"
    ) as mock_post, patch("tooluniverse.foldseek_tool.time.sleep"):
        mock_get.side_effect = [pdb_file_resp, status_resp, result_resp]
        mock_post.return_value = ticket_resp

        result = tool.run({"pdb_id": "4HHB", "database": "pdb100"})

    assert result["status"] == "success"
    submitted_data = mock_post.call_args.kwargs["data"]
    assert submitted_data["mode"] == "3diaa"


def test_explicit_mode_is_respected():
    tool = _tool()

    pdb_file_resp = _resp(200, text="ATOM ...")
    ticket_resp = _resp(200, {"id": "ticket123"})
    status_resp = _resp(200, {"status": "COMPLETE"})
    result_resp = _resp(200, {"results": []})

    with patch("tooluniverse.foldseek_tool.requests.get") as mock_get, patch(
        "tooluniverse.foldseek_tool.requests.post"
    ) as mock_post, patch("tooluniverse.foldseek_tool.time.sleep"):
        mock_get.side_effect = [pdb_file_resp, status_resp, result_resp]
        mock_post.return_value = ticket_resp

        tool.run({"pdb_id": "4HHB", "database": "pdb100", "mode": "tmalign"})

    submitted_data = mock_post.call_args.kwargs["data"]
    assert submitted_data["mode"] == "tmalign"
