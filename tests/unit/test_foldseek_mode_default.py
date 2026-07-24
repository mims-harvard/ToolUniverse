"""Regression guard for Fix-R24A-1: Foldseek_search_structure's `mode`
parameter had two disagreeing defaults -- the JSON schema declared
"3diaa" but the Python code's own fallback was `arguments.get("mode",
"tmalign")`. Confirmed live: with the corrected "3diaa" default, searching
1M17 (EGFR kinase domain) against pdb100 correctly returns other EGFR
mutant structures at ~99% identity; with "tmalign" it returns unrelated,
weakly-scoring hits. An omitted `mode` argument was silently running the
wrong (slower, less specific) search mode. The schema description also had
a copy-paste typo labeling both options "tmalign"; fixed to name the fast
default "3diaa".
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.foldseek_tool import FoldseekTool

pytestmark = pytest.mark.unit


def _tool():
    return FoldseekTool({"name": "foldseek_test", "fields": {"operation": "search"}})


def _mock_flow():
    """requests.post -> ticket submit; requests.get -> [status, result]."""
    post_resp = MagicMock()
    post_resp.status_code = 200
    post_resp.json.return_value = {"id": "ticket123"}

    status_resp = MagicMock()
    status_resp.status_code = 200
    status_resp.json.return_value = {"status": "COMPLETE"}

    result_resp = MagicMock()
    result_resp.status_code = 200
    result_resp.json.return_value = {"results": [{"alignments": [[]]}]}

    return post_resp, status_resp, result_resp


class TestModeDefault:
    def test_omitted_mode_submits_3diaa(self):
        tool = _tool()
        post_resp, status_resp, result_resp = _mock_flow()

        with (
            patch(
                "tooluniverse.foldseek_tool.requests.post", return_value=post_resp
            ) as mock_post,
            patch(
                "tooluniverse.foldseek_tool.requests.get",
                side_effect=[status_resp, result_resp],
            ),
        ):
            tool.run({"sequence": "MKV", "database": "pdb100"})

        submitted_data = mock_post.call_args.kwargs["data"]
        assert submitted_data["mode"] == "3diaa"

    def test_explicit_mode_still_forwarded(self):
        tool = _tool()
        post_resp, status_resp, result_resp = _mock_flow()

        with (
            patch(
                "tooluniverse.foldseek_tool.requests.post", return_value=post_resp
            ) as mock_post,
            patch(
                "tooluniverse.foldseek_tool.requests.get",
                side_effect=[status_resp, result_resp],
            ),
        ):
            tool.run({"sequence": "MKV", "database": "pdb100", "mode": "tmalign"})

        submitted_data = mock_post.call_args.kwargs["data"]
        assert submitted_data["mode"] == "tmalign"
