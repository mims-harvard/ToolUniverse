"""Fix-47-1 / Fix-47-5: an openFDA request that FAILS must not be reported as
an empty answer about the drug.

`search_openfda` handled `NOT_FOUND` richly and let every other upstream error
fall off the end of the branch as a bare `None`, which the CLI renders as
`{"result": null}`. Confirmed live against api.fda.gov/drug/label.json:
adding one undeclared query parameter to an otherwise correct search is
answered by openFDA with HTTP 400
`{"error":{"code":"BAD_REQUEST","message":"Invalid parameter: section"}}`,
and `FDA_get_boxed_warning_info_by_drug_name
{"drug_name":"tramadol","section":"boxed"}` returned `{"result": null}` --
indistinguishable from "tramadol has no boxed warning", for a drug whose
label carries one. openFDA reports rate limiting and server errors the same
way, and ~157 tools route through this function.

Fix-47-5 covers the transport half: the calls carried no `timeout=` and
decoded with a bare `.json()`, so openFDA's HTML error pages surfaced as
"Validation error: Expecting value: line 1 column 1 (char 0)".
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse import openfda_tool
from tooluniverse.openfda_tool import search_openfda

pytestmark = pytest.mark.unit

# Deliberately a two-token name. A NOT_FOUND on a single-token name-based
# query triggers the closest-name fallback, which difflib-scores the whole
# bundled FDA drug list and blows the 60s per-test timeout; these tests are
# about the error envelope, not about that fallback (which has its own
# coverage in tests/unit/test_fda_label_not_found_names_searched_field.py).
_SEARCH_FIELDS = {
    ("openfda.brand_name", "openfda.generic_name"): "tramadol hydrochloride"
}


class _Resp:
    """Minimal stand-in for a requests Response."""

    def __init__(self, payload=None, *, raises=None, status_code=200):
        self._payload = payload
        self._raises = raises
        self.status_code = status_code

    def json(self):
        if self._raises is not None:
            raise self._raises
        return self._payload


def _run(resp_or_exc, **kwargs):
    """Call search_openfda with the network replaced by a single response."""

    def fake_get(url, **_kw):
        if isinstance(resp_or_exc, Exception):
            raise resp_or_exc
        return resp_or_exc

    with patch("tooluniverse.openfda_tool.requests.get", side_effect=fake_get):
        return search_openfda(
            params={"search_fields": dict(_SEARCH_FIELDS), "limit": 100},
            endpoint_url="https://api.fda.gov/drug/label.json",
            return_fields=["boxed_warning"],
            exists=["boxed_warning"],
            **kwargs,
        )


def _bad_request():
    return _Resp(
        {"error": {"code": "BAD_REQUEST", "message": "Invalid parameter: section"}},
        status_code=400,
    )


class TestUpstreamErrorIsNotSilentlyNull:
    def test_bad_request_is_not_none(self):
        """The whole point: a failed request must not come back as None."""
        assert _run(_bad_request()) is not None

    def test_bad_request_reports_error_status(self):
        result = _run(_bad_request())
        assert result["status"] == "error"

    def test_bad_request_preserves_upstream_code_and_message(self):
        result = _run(_bad_request())
        assert result["error"]["code"] == "BAD_REQUEST"
        assert "Invalid parameter: section" in result["error"]["message"]

    def test_bad_request_suggestion_denies_a_conclusion_about_the_drug(self):
        """A caller must not be able to read this as 'no boxed warning'."""
        suggestion = _run(_bad_request())["suggestion"]
        assert "NOT a statement about the drug" in suggestion

    def test_bad_request_suggestion_names_the_rejected_parameter(self):
        """openFDA names the offending key; that name is the whole diagnosis."""
        suggestion = _run(_bad_request())["suggestion"]
        assert "Invalid parameter: section" in suggestion

    def test_bad_request_suggestion_claims_nothing_about_other_parameters(self):
        """An earlier draft listed the parameters that were 'accepted', but by
        this point they are openFDA's own transport keys, not the caller's --
        so the list named things the caller had never sent."""
        suggestion = _run(_bad_request())["suggestion"]
        assert "limit" not in suggestion
        assert "skip" not in suggestion

    def test_error_envelope_keeps_the_not_found_shape(self):
        """Consumers of the NOT_FOUND branch must keep working unchanged."""
        result = _run(_bad_request())
        assert result["results"] == []
        assert result["result_count"] == 0
        assert result["meta"]["total"] == 0

    def test_rate_limit_names_the_api_key_remedy(self):
        result = _run(
            _Resp(
                {
                    "error": {
                        "code": "OVER_RATE_LIMIT",
                        "message": "Too many requests",
                    }
                },
                status_code=429,
            )
        )
        assert result["status"] == "error"
        assert "FDA_API_KEY" in result["suggestion"]

    def test_unknown_error_code_still_reported(self):
        """The branch must not enumerate codes -- anything non-NOT_FOUND counts."""
        result = _run(
            _Resp(
                {"error": {"code": "SERVER_ERROR", "message": "boom"}}, status_code=500
            )
        )
        assert result["status"] == "error"
        assert "SERVER_ERROR" in result["suggestion"]


class TestTransportFailuresAreTransportFailures:
    def test_non_json_body_becomes_bad_json_not_an_exception(self):
        """openFDA's CDN serves HTML under load; that must not raise."""
        result = _run(_Resp(raises=ValueError("Expecting value: line 1 column 1"), status_code=503))
        assert result["status"] == "error"
        assert result["error"]["code"] == "BAD_JSON"

    def test_connection_failure_becomes_transport_error(self):
        result = _run(ConnectionError("connection reset"))
        assert result["status"] == "error"
        assert result["error"]["code"] == "TRANSPORT_ERROR"
        assert "connection reset" in result["error"]["message"]

    def test_requests_are_issued_with_a_timeout(self):
        """No timeout means a stalled openFDA connection hangs the tool."""
        seen = {}

        def fake_get(url, **kw):
            seen.update(kw)
            return _Resp({"meta": {"results": {"total": 0}}, "results": []})

        with patch("tooluniverse.openfda_tool.requests.get", side_effect=fake_get):
            search_openfda(
                params={"search_fields": dict(_SEARCH_FIELDS), "limit": 100},
                endpoint_url="https://api.fda.gov/drug/label.json",
                return_fields=["boxed_warning"],
                exists=["boxed_warning"],
            )
        assert seen.get("timeout") == openfda_tool._OPENFDA_TIMEOUT


class TestSuccessAndNotFoundPathsUnchanged:
    def test_successful_search_still_returns_results(self):
        payload = {
            "meta": {"results": {"skip": 0, "limit": 100, "total": 1}},
            "results": [
                {
                    "boxed_warning": ["Addiction, abuse and misuse."],
                    "openfda": {
                        "brand_name": ["Tramadol"],
                        "generic_name": ["TRAMADOL HYDROCHLORIDE"],
                    },
                }
            ],
        }
        result = _run(_Resp(payload))
        assert result.get("status") != "error"
        assert result["results"][0]["boxed_warning"]

    def test_not_found_still_gets_its_own_rich_suggestion(self):
        """Fix-47-1 must not have swallowed the NOT_FOUND branch."""
        result = _run(
            _Resp({"error": {"code": "NOT_FOUND", "message": "No matches found!"}})
        )
        assert result["error"]["code"] == "NOT_FOUND"
        # The NOT_FOUND advice is section-aware; the generic request-error text
        # must not have replaced it.
        assert "NOT a statement about the drug" not in result["suggestion"]
