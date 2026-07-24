"""Depth tests for the scientometrics cluster tools.

Covers the new tools that reuse existing tool classes (no new registration):
  - ORCID_get_fundings / ORCID_get_peer_reviews  (ORCIDTool, new operations)
  - OpenAIRE_search_projects                     (OpenAIRETool, new type=projects)
  - Crossref_search_members / Crossref_get_member(CrossrefRESTTool, config-only)
  - ROR_match_affiliation                        (BaseRESTTool, config-only)

Each tool gets a parse test (real API response shape, mocked HTTP) and an
error-path test verifying run() returns {"status": "error", ...} and never
raises. Real verified ids are used in the fixtures.
"""

import json
import os
import unittest
from unittest.mock import patch, MagicMock

import pytest

from tooluniverse.orcid_tool import ORCIDTool
from tooluniverse.openaire_tool import OpenAIRETool
from tooluniverse.crossref_tool import CrossrefRESTTool
from tooluniverse.base_rest_tool import BaseRESTTool

pytestmark = pytest.mark.unit

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "src",
    "tooluniverse",
    "data",
)


def _load_config(json_name, tool_name):
    with open(os.path.join(DATA_DIR, json_name)) as fh:
        for entry in json.load(fh):
            if entry.get("name") == tool_name:
                return entry
    raise KeyError(f"{tool_name} not found in {json_name}")


def _rest_response(payload, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = payload
    resp.text = json.dumps(payload)
    resp.headers = {"content-type": "application/json"}
    return resp


def _orcid_response(payload, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = payload
    resp.text = json.dumps(payload)
    return resp


# --------------------------------------------------------------------------
# ORCID_get_fundings
# --------------------------------------------------------------------------
ORCID_FUNDINGS_PAYLOAD = {
    "group": [
        {
            "funding-summary": [
                {
                    "put-code": 111,
                    "title": {
                        "title": {"value": "ADVANCE Leadership Award: Women in Science"}
                    },
                    "type": "award",
                    "organization": {
                        "name": "National Science Foundation",
                        "address": {"country": "US"},
                    },
                    "start-date": {"year": {"value": "1994"}},
                    "end-date": None,
                    "url": None,
                    "external-ids": {
                        "external-id": [
                            {
                                "external-id-type": "grant_number",
                                "external-id-value": "5F31MH010500-03",
                            }
                        ]
                    },
                }
            ]
        }
    ]
}


class TestORCIDGetFundings(unittest.TestCase):
    def _tool(self):
        return ORCIDTool(_load_config("orcid_tools.json", "ORCID_get_fundings"))

    def test_parses_funding_records(self):
        """Parses funding records."""
        with patch("tooluniverse.orcid_tool.requests.get") as get:
            get.return_value = _orcid_response(ORCID_FUNDINGS_PAYLOAD)
            out = self._tool().run(
                {"operation": "get_fundings", "orcid": "0000-0001-5109-3700"}
            )
        assert out["status"] == "success"
        assert out["num_fundings"] == 1
        rec = out["data"][0]
        assert rec["title"].startswith("ADVANCE Leadership Award")
        assert rec["organization"] == "National Science Foundation"
        assert rec["organization_country"] == "US"
        assert rec["external_ids"][0]["external-id-value"] == "5F31MH010500-03"

    def test_missing_orcid_returns_error(self):
        """Missing orcid returns error."""
        out = self._tool().run({"operation": "get_fundings"})
        assert out["status"] == "error"

    def test_http_404_returns_error_not_raise(self):
        """Http 404 returns error not raise."""
        with patch("tooluniverse.orcid_tool.requests.get") as get:
            get.return_value = _orcid_response({"error": "not found"}, status_code=404)
            out = self._tool().run(
                {"operation": "get_fundings", "orcid": "0000-0000-0000-0000"}
            )
        assert out["status"] == "error"


# --------------------------------------------------------------------------
# ORCID_get_peer_reviews
# --------------------------------------------------------------------------
ORCID_PEER_REVIEWS_PAYLOAD = {
    "group": [
        {
            "peer-review-group": [
                {
                    "peer-review-summary": [
                        {
                            "put-code": 222,
                            "reviewer-role": "reviewer",
                            "review-type": "review",
                            "review-group-id": "issn:1476-4687",
                            "convening-organization": {
                                "name": "Springer Nature",
                                "address": {"country": "GB"},
                            },
                            "completion-date": {"year": {"value": "2020"}},
                            "review-url": {"value": "https://example.org/r/1"},
                        }
                    ]
                }
            ]
        }
    ]
}


class TestORCIDGetPeerReviews(unittest.TestCase):
    def _tool(self):
        return ORCIDTool(_load_config("orcid_tools.json", "ORCID_get_peer_reviews"))

    def test_parses_peer_review_records(self):
        """Parses peer review records."""
        with patch("tooluniverse.orcid_tool.requests.get") as get:
            get.return_value = _orcid_response(ORCID_PEER_REVIEWS_PAYLOAD)
            out = self._tool().run(
                {"operation": "get_peer_reviews", "orcid": "0000-0001-5109-3700"}
            )
        assert out["status"] == "success"
        assert out["num_peer_reviews"] == 1
        rec = out["data"][0]
        assert rec["reviewer_role"] == "reviewer"
        assert rec["review_type"] == "review"
        assert rec["convening_organization"] == "Springer Nature"
        assert rec["convening_organization_country"] == "GB"
        assert rec["review_url"] == "https://example.org/r/1"

    def test_missing_orcid_returns_error(self):
        """Missing orcid returns error."""
        out = self._tool().run({"operation": "get_peer_reviews"})
        assert out["status"] == "error"

    def test_http_404_returns_error_not_raise(self):
        """Http 404 returns error not raise."""
        with patch("tooluniverse.orcid_tool.requests.get") as get:
            get.return_value = _orcid_response({}, status_code=404)
            out = self._tool().run(
                {"operation": "get_peer_reviews", "orcid": "0000-0000-0000-0000"}
            )
        assert out["status"] == "error"


# --------------------------------------------------------------------------
# OpenAIRE_search_projects
# --------------------------------------------------------------------------
OPENAIRE_PROJECTS_PAYLOAD = {
    "response": {
        "header": {"total": {"$": 338492}},
        "results": {
            "result": [
                {
                    "metadata": {
                        "oaf:entity": {
                            "oaf:project": {
                                "code": {"$": "1067696"},
                                "acronym": None,
                                "title": {"$": "Improving sexual health in men"},
                                "startdate": {"$": "2010-01-01"},
                                "enddate": {"$": "2013-12-31"},
                                "fundedamount": {"$": "500000"},
                                "totalcost": {"$": "500000"},
                                "currency": {"$": "AUD"},
                                "websiteurl": {"$": "https://example.org"},
                                "fundingtree": {
                                    "funder": {
                                        "name": {
                                            "$": "National Health and Medical "
                                            "Research Council (NHMRC)"
                                        },
                                        "shortname": {"$": "NHMRC"},
                                    },
                                    "funding_level_0": {
                                        "name": {"$": "Project Grants"}
                                    },
                                },
                            }
                        }
                    }
                }
            ]
        },
    }
}


class TestOpenAIRESearchProjects(unittest.TestCase):
    def _tool(self):
        return OpenAIRETool(
            _load_config("openaire_tools.json", "OpenAIRE_search_projects")
        )

    def test_parses_project_records(self):
        """Parses project records."""
        with patch("tooluniverse.openaire_tool.requests.get") as get:
            resp = MagicMock()
            resp.json.return_value = OPENAIRE_PROJECTS_PAYLOAD
            resp.raise_for_status = MagicMock()
            get.return_value = resp
            out = self._tool().run(
                {"query": "cancer", "max_results": 1, "type": "projects"}
            )
        assert out["status"] == "success"
        data = out["data"]
        assert data["status"] == "success"
        # total comes from the response header, not the page length
        assert data["total_results"] == 338492
        assert data["returned"] == 1
        rec = data["results"][0]
        assert rec["code"] == "1067696"
        assert rec["funder_shortname"] == "NHMRC"
        assert rec["funding_stream"] == "Project Grants"
        assert rec["title"].startswith("Improving sexual health")

    def test_uses_keywords_param_not_query(self):
        """Uses keywords param not query."""
        # The OpenAIRE API rejects the legacy `query` param (HTTP 400);
        # the request must use `keywords`.
        with patch("tooluniverse.openaire_tool.requests.get") as get:
            resp = MagicMock()
            resp.json.return_value = {"response": {}}
            resp.raise_for_status = MagicMock()
            get.return_value = resp
            self._tool().run({"query": "cancer", "max_results": 1, "type": "projects"})
            _, kwargs = get.call_args
            assert kwargs["params"].get("keywords") == "cancer"
            assert "query" not in kwargs["params"]

    def test_missing_query_returns_error(self):
        """Missing query returns error."""
        out = self._tool().run({"max_results": 1, "type": "projects"})
        # run() wraps the error inside data with an inner status of "error"
        assert out["data"]["status"] == "error"

    def test_http_failure_returns_error_not_raise(self):
        """Http failure returns error not raise."""
        import requests

        with patch("tooluniverse.openaire_tool.requests.get") as get:
            get.side_effect = requests.RequestException("network down")
            out = self._tool().run(
                {"query": "cancer", "max_results": 1, "type": "projects"}
            )
        assert out["data"]["status"] == "error"


# --------------------------------------------------------------------------
# Crossref_search_members
# --------------------------------------------------------------------------
CROSSREF_MEMBERS_LIST_PAYLOAD = {
    "message": {
        "total-results": 1,
        "items": [
            {
                "id": 340,
                "primary-name": "Public Library of Science (PLoS)",
                "location": "San Francisco, CA",
                "counts": {"total-dois": 100000},
            }
        ],
    }
}


class TestCrossrefSearchMembers(unittest.TestCase):
    def _tool(self):
        return CrossrefRESTTool(
            _load_config("crossref_tools.json", "Crossref_search_members")
        )

    def test_parses_member_list(self):
        """Parses member list."""
        with patch("tooluniverse.base_rest_tool.request_with_retry") as req:
            req.return_value = _rest_response(CROSSREF_MEMBERS_LIST_PAYLOAD)
            out = self._tool().run({"query": "plos", "limit": 2})
        assert out["status"] == "success"
        assert out["count"] == 1
        assert out["data"][0]["id"] == 340
        assert out["data"][0]["primary-name"].startswith("Public Library of Science")

    def test_limit_maps_to_rows_param(self):
        """Limit maps to rows param."""
        with patch("tooluniverse.base_rest_tool.request_with_retry") as req:
            req.return_value = _rest_response(CROSSREF_MEMBERS_LIST_PAYLOAD)
            self._tool().run({"query": "plos", "limit": 2})
            _, kwargs = req.call_args
            assert kwargs["params"].get("rows") == 2
            assert kwargs["params"].get("query") == "plos"

    def test_http_error_returns_error_not_raise(self):
        """Http error returns error not raise."""
        with patch("tooluniverse.base_rest_tool.request_with_retry") as req:
            req.return_value = _rest_response({"error": "bad"}, status_code=500)
            out = self._tool().run({"query": "plos"})
        assert out["status"] == "error"


# --------------------------------------------------------------------------
# Crossref_get_member
# --------------------------------------------------------------------------
CROSSREF_MEMBER_DETAIL_PAYLOAD = {
    "message": {
        "id": 78,
        "primary-name": "Elsevier BV",
        "location": "Amsterdam",
        "counts": {
            "current-dois": 100,
            "backfile-dois": 200,
            "total-dois": 24961410,
        },
        "breakdowns": {"dois-by-issued-year": [[2020, 1000], [2021, 2000]]},
        "prefixes": ["10.1016"],
    }
}


class TestCrossrefGetMember(unittest.TestCase):
    def _tool(self):
        return CrossrefRESTTool(
            _load_config("crossref_tools.json", "Crossref_get_member")
        )

    def test_parses_member_detail(self):
        """Parses member detail."""
        with patch("tooluniverse.base_rest_tool.request_with_retry") as req:
            req.return_value = _rest_response(CROSSREF_MEMBER_DETAIL_PAYLOAD)
            out = self._tool().run({"member_id": "78"})
        assert out["status"] == "success"
        assert out["data"]["primary-name"] == "Elsevier BV"
        assert out["data"]["counts"]["total-dois"] == 24961410
        assert "dois-by-issued-year" in out["data"]["breakdowns"]

    def test_member_id_in_url(self):
        """Member id in url."""
        with patch("tooluniverse.base_rest_tool.request_with_retry") as req:
            req.return_value = _rest_response(CROSSREF_MEMBER_DETAIL_PAYLOAD)
            self._tool().run({"member_id": "78"})
            args, _ = req.call_args
            # URL is the third positional arg: (session, "GET", url, ...)
            assert args[2].endswith("/members/78")

    def test_http_error_returns_error_not_raise(self):
        """Http error returns error not raise."""
        with patch("tooluniverse.base_rest_tool.request_with_retry") as req:
            req.return_value = _rest_response({"error": "bad"}, status_code=404)
            out = self._tool().run({"member_id": "99999999"})
        assert out["status"] == "error"


# --------------------------------------------------------------------------
# ROR_match_affiliation
# --------------------------------------------------------------------------
ROR_AFFILIATION_PAYLOAD = {
    "number_of_results": 2,
    "items": [
        {
            "substring": "Harvard University",
            "score": 1.0,
            "chosen": True,
            "matching_type": "PHRASE",
            "organization": {
                "id": "https://ror.org/03vek6s52",
                "names": [{"value": "Harvard University"}],
            },
        },
        {
            "substring": "Department of Chemistry",
            "score": 0.5,
            "chosen": False,
            "matching_type": "COMMON TERMS",
            "organization": {"id": "https://ror.org/00000000z"},
        },
    ],
}


class TestRORMatchAffiliation(unittest.TestCase):
    def _tool(self):
        return BaseRESTTool(_load_config("ror_tools.json", "ROR_match_affiliation"))

    def test_parses_chosen_match(self):
        """Parses chosen match."""
        with patch("tooluniverse.base_rest_tool.request_with_retry") as req:
            req.return_value = _rest_response(ROR_AFFILIATION_PAYLOAD)
            out = self._tool().run(
                {"affiliation": "Department of Chemistry, Harvard University"}
            )
        assert out["status"] == "success"
        chosen = [i for i in out["data"]["items"] if i.get("chosen")]
        assert len(chosen) == 1
        assert chosen[0]["organization"]["id"] == "https://ror.org/03vek6s52"

    def test_affiliation_sent_as_query_param(self):
        """Affiliation sent as query param."""
        with patch("tooluniverse.base_rest_tool.request_with_retry") as req:
            req.return_value = _rest_response(ROR_AFFILIATION_PAYLOAD)
            self._tool().run({"affiliation": "Harvard University"})
            _, kwargs = req.call_args
            assert kwargs["params"].get("affiliation") == "Harvard University"

    def test_http_error_returns_error_not_raise(self):
        """Http error returns error not raise."""
        with patch("tooluniverse.base_rest_tool.request_with_retry") as req:
            req.return_value = _rest_response({"error": "bad"}, status_code=500)
            out = self._tool().run({"affiliation": "nowhere"})
        assert out["status"] == "error"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
