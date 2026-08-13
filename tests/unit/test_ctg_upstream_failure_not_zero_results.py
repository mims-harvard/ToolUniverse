"""A ClinicalTrials.gov request that never ran must not be reported as zero hits.

Fix Round 48. `execute_RESTful_query` collapsed every failure mode into
`False` and printed the reason to stdout, so `search_clinical_trials` could
only say "No studies found for the given query parameters" -- and, when the
phase gate was active, went on to blame that filter for the emptiness.

Measured live 2026-08-13:

    search_clinical_trials {"intervention": "[177Lu]Lu-PSMA-617"}
      -> status error, "No studies found for the given query parameters.
         Please examine your input and try different parameters. This search
         excludes phase-1-only, phase-NA, and observational studies by
         default..."

    curl 'https://clinicaltrials.gov/api/v2/studies?query.term=%5B177Lu%5DLu-PSMA-617'
      -> HTTP 400
         "Error parsing query in Other terms: extraneous input '[' expecting ..."

    search_clinical_trials {"intervention": "177Lu-PSMA-617"}
      -> total_count 46

`[177Lu]Lu-PSMA-617` is standard EANM/IUPAC radiopharmaceutical nomenclature
and appears in trial titles this very tool returns, so it is a natural query.
The caller was told no trials exist, and pointed at the wrong cause, for a
query the API had refused to run.
"""

import json
from pathlib import Path

import pytest

from tooluniverse import restful_tool
from tooluniverse.restful_tool import execute_RESTful_query_detailed

pytestmark = pytest.mark.unit

CONFIG = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "tooluniverse"
    / "data"
    / "clinicaltrials_gov_tools.json"
)


def _search_config():
    with open(CONFIG) as fh:
        for cfg in json.load(fh):
            if cfg["name"] == "search_clinical_trials":
                return cfg
    raise AssertionError("search_clinical_trials not in clinicaltrials_gov_tools.json")


class _Response:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        if self._payload is None:
            import requests

            raise requests.exceptions.JSONDecodeError("no json", "", 0)
        return self._payload


def _patch_get(monkeypatch, response):
    monkeypatch.setattr(
        restful_tool.requests, "get", lambda url, params=None: response
    )


def test_http_400_body_is_returned_as_the_reason(monkeypatch):
    """The parse diagnostic lives in the BODY of the 400, not the status line."""
    _patch_get(
        monkeypatch,
        _Response(
            status_code=400,
            text="Error parsing query in Other terms: extraneous input '['",
        ),
    )
    result, reason = execute_RESTful_query_detailed("http://x")

    assert result is False
    assert "400" in reason
    assert "extraneous input" in reason


def test_successful_response_reports_no_reason(monkeypatch):
    _patch_get(monkeypatch, _Response(payload={"studies": [{"a": 1}]}))
    result, reason = execute_RESTful_query_detailed("http://x")

    assert reason is None
    assert result == {"studies": [{"a": 1}]}


def test_api_error_field_is_surfaced(monkeypatch):
    _patch_get(monkeypatch, _Response(payload={"error": "bad field"}))
    result, reason = execute_RESTful_query_detailed("http://x")

    assert result is False
    assert "bad field" in reason


def test_network_exception_is_surfaced(monkeypatch):
    def boom(url, params=None):
        raise OSError("connection reset")

    monkeypatch.setattr(restful_tool.requests, "get", boom)
    result, reason = execute_RESTful_query_detailed("http://x")

    assert result is False
    assert "connection reset" in reason


def test_boolean_wrapper_contract_is_unchanged(monkeypatch):
    """Every other caller still branches on truthiness and must be unaffected."""
    _patch_get(monkeypatch, _Response(status_code=400, text="nope"))
    assert restful_tool.execute_RESTful_query("http://x") is False

    _patch_get(monkeypatch, _Response(payload={"ok": 1}))
    assert restful_tool.execute_RESTful_query("http://x") == {"ok": 1}


def test_search_reports_the_upstream_failure_rather_than_zero_studies(monkeypatch):
    """End-to-end: the tool's own error must not claim zero studies."""
    from tooluniverse.ctg_tool import ClinicalTrialsSearchTool

    tool = ClinicalTrialsSearchTool(_search_config())
    monkeypatch.setattr(
        "tooluniverse.ctg_tool.execute_RESTful_query_detailed",
        lambda endpoint_url, variables=None: (
            False,
            "HTTP 400: Error parsing query in Intervention / treatment: "
            "extraneous input '['",
        ),
    )

    result = tool.run({"intervention": "[177Lu]Lu-PSMA-617"})

    assert result["status"] == "error"
    error = result["error"]
    # The old message asserted a fact about the trial landscape that the tool
    # had no basis for. It must be gone, not merely supplemented.
    assert "No studies found for the given query parameters" not in error
    assert "400" in error and "extraneous input" in error
    assert "not a report that zero studies exist" in error
