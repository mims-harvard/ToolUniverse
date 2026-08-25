"""Unit tests for CTIS ``status`` filter validation. Network mocked.

CTIS answers an unrecognized ``status`` value with an ordinary empty result set
rather than an error. Passing one through unchecked therefore produced a
confident, successful-looking "there are no such trials" — the wrong conclusion,
and especially easy to hit because the tool's own description talks about
"3=ongoing/recruiting", inviting a caller to pass the word "ongoing".

Status values are now validated at input against the CTIS code set.
"""

import json
from unittest.mock import MagicMock, patch

from tooluniverse.ctis_tool import (
    _CTIS_STATUS_CODES,
    CTISSearchTrialsTool,
    _validate_status,
)

_CONFIG = {
    "name": "CTIS_search_trials_filtered",
    "type": "CTISSearchTrialsTool",
    "parameter": {"type": "object", "properties": {}},
}

_PAYLOAD = {
    "pagination": {"totalRecords": 1, "currentPage": 1, "totalPages": 1},
    "data": [{"ctNumber": "2023-000000-00-00", "ctTitle": "A trial", "ctStatus": 4}],
}


def _tool():
    return CTISSearchTrialsTool(dict(_CONFIG))


def _resp(json_body):
    r = MagicMock()
    r.status_code = 200
    r.json.return_value = json_body
    r.raise_for_status.return_value = None
    return r


def _no_network():
    """Any HTTP call is a failure: rejection must happen before the request."""
    return patch(
        "tooluniverse.ctis_tool.requests.post",
        side_effect=AssertionError("CTIS must not be called with an invalid status"),
    )


# ---------------- invalid values are rejected, not silently searched ---------
def test_garbage_status_is_rejected_without_calling_ctis():
    with _no_network():
        out = _tool().run({"query": "PSMA-617", "status": "bogus_nonsense_value"})

    assert out["status"] == "error"
    assert "bogus_nonsense_value" in out["error"]
    # The error must be actionable: it names the valid codes and their meanings.
    assert "1=Under evaluation" in out["error"]
    assert "8=Ended" in out["error"]


def test_natural_language_status_is_rejected():
    """'ongoing' reads plausible but matches nothing at CTIS."""
    with _no_network():
        out = _tool().run({"query": "cancer", "status": "ongoing"})

    assert out["status"] == "error"
    assert "'ongoing'" in out["error"]


def test_out_of_range_code_is_rejected():
    with _no_network():
        out = _tool().run({"query": "cancer", "status": 99})

    assert out["status"] == "error"
    assert "99" in out["error"]


def test_one_invalid_entry_rejects_the_whole_list():
    with _no_network():
        out = _tool().run({"query": "cancer", "status": [3, "ongoing"]})

    assert out["status"] == "error"


def test_booleans_are_not_accepted_as_status_codes():
    with _no_network():
        out = _tool().run({"query": "cancer", "status": True})

    assert out["status"] == "error"


# ---------------- valid values keep working ---------------------------------
def test_valid_integer_code_reaches_ctis():
    with patch(
        "tooluniverse.ctis_tool.requests.post", return_value=_resp(_PAYLOAD)
    ) as post:
        out = _tool().run({"query": "PSMA-617", "status": [4]})

    assert out["status"] == "success"
    assert out["metadata"]["total_records"] == 1
    body = post.call_args.kwargs["json"]
    assert body["searchCriteria"]["status"] == [4]


def test_numeric_string_is_normalized_to_an_integer_code():
    with patch(
        "tooluniverse.ctis_tool.requests.post", return_value=_resp(_PAYLOAD)
    ) as post:
        out = _tool().run({"query": "cancer", "status": "3"})

    assert out["status"] == "success"
    body = post.call_args.kwargs["json"]
    assert body["searchCriteria"]["status"] == [3]


def test_every_documented_code_validates():
    for code in _CTIS_STATUS_CODES:
        codes, error = _validate_status(code)
        assert error is None, code
        assert codes == [code]


def test_status_absent_is_not_an_error():
    with patch("tooluniverse.ctis_tool.requests.post", return_value=_resp(_PAYLOAD)):
        out = _tool().run({"query": "cancer"})
    assert out["status"] == "success"


def test_schema_declares_the_status_code_set():
    """The runtime constraint must also be declared in the published schema."""
    from importlib.resources import files

    data = json.loads((files("tooluniverse.data") / "ctis_tools.json").read_text())
    cfg = next(t for t in data if t["name"] == "CTIS_search_trials_filtered")
    enum = cfg["parameter"]["properties"]["status"]["items"]["enum"]
    for code in _CTIS_STATUS_CODES:
        assert code in enum
        assert str(code) in enum
