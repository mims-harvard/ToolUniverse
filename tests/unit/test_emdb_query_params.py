"""Regression guard for Fix-R18A-1: EMDBRESTTool._build_url only substituted
`{placeholder}` tokens present in the endpoint template, so a declared
parameter with no matching placeholder (e.g. EMDB_search_structures's
`rows`, whose template is "https://.../search/{query}" with no `{rows}`
token) was silently dropped -- confirmed live that rows=2 and rows=10 both
returned the same 10 results, since the raw EMDB API honors `?rows=N` as a
query string parameter but the tool never sent one. _build_url now returns
unmatched args separately so they can be passed through as query params.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.emdb_tool import EMDBRESTTool

pytestmark = pytest.mark.unit


def _tool(endpoint):
    return EMDBRESTTool(
        {"name": "EMDB_search_structures", "fields": {"endpoint": endpoint}}
    )


def test_build_url_returns_unmatched_args_as_query_params():
    tool = _tool("https://www.ebi.ac.uk/emdb/api/search/{query}")

    url, params = tool._build_url({"query": "ribosome", "rows": 2})

    assert url == "https://www.ebi.ac.uk/emdb/api/search/ribosome"
    assert params == {"rows": 2}


def test_build_url_no_leftover_params_when_all_args_match_placeholders():
    tool = _tool("https://www.ebi.ac.uk/emdb/api/entry/{emdb_id}")

    url, params = tool._build_url({"emdb_id": "EMD-53925"})

    assert url == "https://www.ebi.ac.uk/emdb/api/entry/EMD-53925"
    assert params == {}


def test_run_passes_leftover_args_as_query_params():
    tool = _tool("https://www.ebi.ac.uk/emdb/api/search/{query}")

    captured = {}

    def fake_request_with_retry(session, method, url, **kwargs):
        captured["url"] = url
        captured["params"] = kwargs.get("params")
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = [{"id": "EMD-1"}, {"id": "EMD-2"}]
        return resp

    with patch(
        "tooluniverse.emdb_tool.request_with_retry",
        side_effect=fake_request_with_retry,
    ):
        result = tool.run({"query": "ribosome", "rows": 2})

    assert result["status"] == "success"
    assert captured["params"] == {"rows": 2}
    assert "rows" not in captured["url"]
