"""PROSITE_search reported "Expecting value: line 1 column 1" when nothing matched.

InterPro answers a search with no hits as HTTP 204 with an empty body. The tool
called response.json() on it, so a plain "no results" looked like a broken API.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.prosite_tool import PROSITETool

pytestmark = pytest.mark.unit


def _search(content, body=None, status=200):
    response = MagicMock(status_code=status, content=content)
    if body is None:
        response.json.side_effect = ValueError("Expecting value: line 1 column 1")
    else:
        response.json.return_value = body
    tool = PROSITETool({"name": "PROSITE_search", "fields": {"endpoint": "search"}})
    with patch("tooluniverse.prosite_tool.requests.get", return_value=response):
        return tool.run({"query": "zzqxjvwk"})


def test_empty_204_body_is_zero_results_not_a_parse_error():
    result = _search(b"", status=204)
    assert result["status"] == "success"
    assert result["data"] == []
    assert result["metadata"]["total_results"] == 0


def test_hits_are_still_returned():
    body = {
        "count": 1,
        "results": [
            {
                "metadata": {
                    "accession": "PS00028",
                    "name": {
                        "name": "Zinc finger C2H2 type domain signature",
                        "short": "",
                    },
                    "type": "conserved_site",
                    "source_database": "prosite",
                    "integrated": "IPR013087",
                }
            }
        ],
    }
    result = _search(b"{...}", body)
    assert [r["accession"] for r in result["data"]] == ["PS00028"]
    assert result["metadata"]["total_results"] == 1
