"""DONKI moved host, and the old one now serves a web page.

The tools called kauai.ccmc.gsfc.nasa.gov/DONKI/WS/get/*, which answers 200
with 60444 bytes of HTML -- the same page for every path, and the same page
api.nasa.gov/DONKI/* returns when given a key, so that route proxies to it.
Its title is "CCMC Announcements | NASA CCMC", and the page itself links to
https://ccmc.gsfc.nasa.gov/DONKI/ as the current home.

The service is there, unauthenticated. Measured 2026-10-04 on
ccmc.gsfc.nasa.gov/DONKI/WS/get/:

    CME 2024-01-01..2024-02-29   200   207 records
    FLR                          200   115
    GST                          200     0  (7 for May-June)
    SEP                          200    27
    IPS                          200    22
    HSS                          200     3

The new host caps a query at 60 days, which the old one did not:

    90 days -> 400 "API Error: Date range cannot exceed 60 days."

Four of the six tools shipped examples spanning 90 to 180 days, so repointing
alone would have traded an HTML page for a 400. nasa_donki goes from 18
failures to 18 passing.
"""

import datetime
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

DATA = Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "data"
DONKI_MAX_DAYS = 60


def _tools():
    return json.loads((DATA / "nasa_donki_tools.json").read_text("utf-8"))


def test_no_tool_still_calls_the_old_host():
    raw = (DATA / "nasa_donki_tools.json").read_text("utf-8")

    assert "kauai.ccmc.gsfc.nasa.gov" not in raw, (
        "that host answers 200 with a web page, so the failure looks like bad "
        "data rather than a moved service"
    )


def test_every_endpoint_points_at_the_current_host():
    for tool in _tools():
        endpoint = (tool.get("fields") or {}).get("endpoint", "")
        assert endpoint.startswith("https://ccmc.gsfc.nasa.gov/DONKI/WS/get/"), (
            f"{tool['name']}: {endpoint}"
        )


def test_the_six_event_types_are_all_covered():
    endpoints = {
        (tool.get("fields") or {}).get("endpoint", "").rsplit("/", 1)[-1]
        for tool in _tools()
    }

    assert endpoints == {"CME", "FLR", "GST", "SEP", "IPS", "HSS"}


def test_no_example_exceeds_the_sixty_day_ceiling():
    """The old host had no limit; four tools shipped 90-to-180-day examples."""
    too_wide = []
    for tool in _tools():
        for example in tool.get("test_examples") or []:
            start, end = example.get("startDate"), example.get("endDate")
            if not (start and end):
                continue
            span = (
                datetime.date.fromisoformat(end) - datetime.date.fromisoformat(start)
            ).days
            if span > DONKI_MAX_DAYS:
                too_wide.append((tool["name"], start, end, span))

    assert not too_wide, (
        "the host answers 400 'Date range cannot exceed 60 days' for these: "
        f"{too_wide}"
    )


def test_the_examples_still_span_a_useful_window():
    """Trimming must not collapse them to a single day."""
    spans = []
    for tool in _tools():
        for example in tool.get("test_examples") or []:
            start, end = example.get("startDate"), example.get("endDate")
            if start and end:
                spans.append(
                    (
                        datetime.date.fromisoformat(end)
                        - datetime.date.fromisoformat(start)
                    ).days
                )

    assert spans
    # The narrowest is a pre-existing 6-day window, not one of the trims.
    assert min(spans) >= 6, spans
    assert max(spans) <= DONKI_MAX_DAYS
    assert max(spans) >= 30, "a trim that leaves only tiny windows tests less"


def test_a_server_error_is_named_in_the_shared_rest_path():
    """"MouseMine_search API error" for a 504 reads like a bad request."""
    source = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "tooluniverse"
        / "base_rest_tool.py"
    ).read_text("utf-8")

    assert "elif 500 <= response.status_code < 600:" in source
    assert "failing on" in source
    # A 4xx must keep its own handling: a challenge, or alternatives, or the
    # plain message.
    assert "cloudflare_challenge(response)" in source
    assert "unreachable_alternatives" in source
