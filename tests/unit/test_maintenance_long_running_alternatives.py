"""Three upstreams that cannot be fixed, reported so a reader knows that.

From the analysis of what was left after the sweep triage:

  GDC           announced maintenance: 503 and a 39 KB "undergoing
                maintenance" page for every request, /status included
  proteinsplus  not broken -- poll_interval 15 s and max_wait_time 1800 s, so
                one call may block for half an hour and six tools can never
                fit the sweep's 600 s budget
  POWO          a Cloudflare challenge, with usable but non-equivalent
                alternatives (IPNI for names, GBIF for taxonomy)

None of the three is a defect to repair. All three were reported as though
they were: "HTTP Error 503", "TIMEOUT", and "POWO_search_plants API error".
"""

import importlib.util
import json
from pathlib import Path
from urllib.error import HTTPError

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "src" / "tooluniverse" / "data"


def _sweep():
    spec = importlib.util.spec_from_file_location(
        "test_all_tools_reasons", ROOT / "scripts" / "test_all_tools.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Body:
    def __init__(self, text):
        self._text = text.encode("utf-8")

    def read(self):
        return self._text


def _http_error(code, body):
    error = HTTPError("https://api.gdc.cancer.gov/status", code, "err", {}, None)
    error.read = _Body(body).read
    return error


def test_the_gdc_maintenance_page_is_recognised():
    from tooluniverse.gdc_tool import _maintenance_error

    error = _http_error(
        503, "<html>The GDC is currently undergoing maintenance.</html>"
    )

    message = str(_maintenance_error(error))

    assert "scheduled maintenance" in message
    assert "Nothing to configure" in message


def test_an_ordinary_503_is_not_called_maintenance():
    """A real outage must not be explained away as a planned window."""
    from tooluniverse.gdc_tool import _maintenance_error

    assert _maintenance_error(_http_error(503, "Service Unavailable")) is None
    assert _maintenance_error(_http_error(500, "undergoing maintenance")) is None


def test_the_detector_never_raises_on_an_unreadable_body():
    from tooluniverse.gdc_tool import _maintenance_error

    error = HTTPError("https://api.gdc.cancer.gov/", 503, "err", {}, None)

    def boom():
        raise OSError("socket closed")

    error.read = boom

    assert _maintenance_error(error) is None


def test_gdc_raises_rather_than_swallowing_a_non_maintenance_error():
    """The explicit branch matters.

    `raise maintenance from error if maintenance else error` parses as
    `raise maintenance from (...)`, so it raised None for every other HTTP
    error. ruff accepts it; ast shows the cause is the conditional.
    """
    source = (ROOT / "src" / "tooluniverse" / "gdc_tool.py").read_text("utf-8")

    assert "if maintenance is not None:" in source
    assert "raise maintenance from error if maintenance else error" not in source
    assert source.count("raise maintenance from error") == 2


def test_proteinsplus_declares_that_it_polls_for_too_long():
    tools = json.loads((DATA / "proteinsplus_tools.json").read_text("utf-8"))

    assert tools
    for tool in tools:
        assert tool.get("long_running") is True, tool["name"]


def test_the_runner_skips_a_long_running_tool():
    source = (ROOT / "scripts" / "test_new_tools.py").read_text("utf-8")

    assert 'tool.get("long_running")' in source
    assert "skipped_long_running" in source
    assert "Skipped long running:" in source


def test_the_sweep_names_whichever_skip_reason_applies():
    sweep = _sweep()

    long_running = sweep.normalize_result(
        {"skipped": 6, "skipped_long_running": 6, "tests_run": 0}
    )
    local_input = sweep.normalize_result(
        {"skipped": 1, "skipped_local_input": 1, "tests_run": 0}
    )
    credential = sweep.normalize_result({"skipped": 2, "tests_run": 0})
    mixed = sweep.normalize_result(
        {
            "skipped": 4,
            "skipped_long_running": 1,
            "skipped_local_input": 1,
            "tests_run": 0,
        }
    )

    assert "poll an upstream job" in sweep._format_result_status(long_running)
    assert "credential" not in sweep._format_result_status(long_running)
    assert "input file the caller supplies" in sweep._format_result_status(local_input)
    assert "credential" in sweep._format_result_status(credential)

    both = sweep._format_result_status(mixed)
    assert "1 poll an upstream job" in both
    assert "1 need an input file" in both
    assert "2 need a credential" in both


def test_powo_carries_the_alternatives_it_is_not_repointed_to():
    tools = json.loads((DATA / "powo_tools.json").read_text("utf-8"))

    for tool in tools:
        text = (tool.get("fields") or {}).get("unreachable_alternatives", "")
        assert "ipni.org" in text, tool["name"]
        assert "gbif.org" in text, tool["name"]
        # The reason they are pointers and not a repoint.
        assert "drop-in replacement" in text
        assert "not repointed" in text


def test_the_shared_rest_path_appends_configured_alternatives():
    source = (
        ROOT / "src" / "tooluniverse" / "base_rest_tool.py"
    ).read_text("utf-8")

    assert "unreachable_alternatives" in source
    assert "response.status_code >= 400 and alternatives" in source, (
        "a 3xx is not a dead upstream and should not get the pointer"
    )
