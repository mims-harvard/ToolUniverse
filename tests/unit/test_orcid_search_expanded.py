"""Regression guard for Fix-R22E-1: ORCID_search_researchers previously hit
ORCID's plain `/search` endpoint, which returns only bare ORCID iDs -- a
caller had to make a separate ORCID_get_profile call per candidate just to
tell same-named researchers apart. Confirmed live that ORCID's own
`/expanded-search` endpoint returns given/family/credit names and
institution affiliations in the same single call. Fixed by switching to it.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.orcid_tool import ORCIDTool

pytestmark = pytest.mark.unit

_EXPANDED_SEARCH_RESPONSE = {
    "expanded-result": [
        {
            "orcid-id": "0000-0002-1992-2684",
            "given-names": "Yann",
            "family-names": "LeCun",
            "credit-name": "Yann LeCun",
            "other-name": ["Yann Le Cun"],
            "institution-name": ["New York University", "Meta"],
        },
        {
            "orcid-id": "0009-0004-0706-6114",
            "given-names": "Yann",
            "family-names": "LeCun",
            "credit-name": None,
            "other-name": [],
            "institution-name": [],
        },
    ],
    "num-found": 1564,
}


def _tool():
    return ORCIDTool({"name": "orcid_test", "parameter": {}})


def _resp(json_body):
    r = MagicMock()
    r.status_code = 200
    r.json.return_value = json_body
    return r


class TestSearchResearchersDisambiguation:
    def test_results_carry_names_and_institutions(self):
        tool = _tool()
        resp = _resp(_EXPANDED_SEARCH_RESPONSE)

        with patch("tooluniverse.orcid_tool.requests.get", return_value=resp) as mock_get:
            result = tool.run({"operation": "search_researchers", "query": "Yann LeCun"})

        assert result["status"] == "success"
        assert mock_get.call_args[0][0].endswith("/expanded-search")
        assert result["total_found"] == 1564
        first = result["data"][0]
        assert first["orcid"] == "0000-0002-1992-2684"
        assert first["family_names"] == "LeCun"
        assert first["credit_name"] == "Yann LeCun"
        assert "New York University" in first["institutions"]

    def test_candidate_with_no_institutions_gets_empty_list_not_missing_key(self):
        tool = _tool()
        resp = _resp(_EXPANDED_SEARCH_RESPONSE)

        with patch("tooluniverse.orcid_tool.requests.get", return_value=resp):
            result = tool.run({"operation": "search_researchers", "query": "Yann LeCun"})

        second = result["data"][1]
        assert second["institutions"] == []
        assert second["credit_name"] is None

    def test_empty_result_set_does_not_crash(self):
        tool = _tool()
        resp = _resp({"expanded-result": [], "num-found": 0})

        with patch("tooluniverse.orcid_tool.requests.get", return_value=resp):
            result = tool.run(
                {"operation": "search_researchers", "query": "zzz_no_such_researcher"}
            )

        assert result["status"] == "success"
        assert result["data"] == []
        assert result["total_found"] == 0
