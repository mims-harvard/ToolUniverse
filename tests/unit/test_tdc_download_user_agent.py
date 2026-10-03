"""TDC's whole breakage was one blocked User-Agent string.

Harvard Dataverse hosts every TDC dataset and answers 403 to the literal
User-Agent "python-requests/x.y" and 200 to anything else. PyTDC downloads with
a bare requests.get, so load_dataset fetched a 199-byte "403 Forbidden" HTML
page instead of the file. Measured against /api/access/datafile/4259569, the
Caco2_Wang file PyTDC asks for:

    default (python-requests/2.32.5)   403      199 bytes  text/html
    ToolUniverse/1.5.4                 200    82501 bytes  text/tab-separated-values
    empty User-Agent                   200    82501 bytes
    curl/8.5.0                         200    82501 bytes

Not a TDC outage and not a Dataverse one: the endpoint, the file ids PyTDC
carries and the data are all fine.

PyTDC then read that HTML as a TSV and called
sys.exit("Please report this error to contact@tdcommons.ai, thanks!").
SystemExit is not an Exception, so it went through every handler and killed the
process -- which is why the sweep reported the dataset and tdc_dataset
categories as "incomplete or invalid test output" rather than as failures.

With a User-Agent supplied, both examples return real data: Caco2_Wang 910 rows
and hERG 655 rows, columns Drug_ID, Drug, Y.
"""

import pytest

import tooluniverse.tdc_dataset_tool as tdc_tool

pytestmark = pytest.mark.unit


def test_a_user_agent_is_supplied_when_the_caller_sets_none():
    import requests

    seen = {}
    original = requests.sessions.Session.request

    def capture(self, method, url, **kwargs):
        seen["headers"] = dict(kwargs.get("headers") or {})
        raise RuntimeError("stop here, the headers are what matter")

    requests.sessions.Session.request = capture
    try:
        with tdc_tool._requests_user_agent("TestAgent/9.9"):
            with pytest.raises(RuntimeError):
                requests.get("https://dataverse.harvard.edu/api/access/datafile/1")
    finally:
        requests.sessions.Session.request = original

    assert seen["headers"].get("User-Agent") == "TestAgent/9.9"


def test_a_user_agent_the_caller_chose_is_left_alone():
    import requests

    seen = {}
    original = requests.sessions.Session.request

    def capture(self, method, url, **kwargs):
        seen["headers"] = dict(kwargs.get("headers") or {})
        raise RuntimeError("stop")

    requests.sessions.Session.request = capture
    try:
        with tdc_tool._requests_user_agent("TestAgent/9.9"):
            with pytest.raises(RuntimeError):
                requests.get(
                    "https://example.invalid/", headers={"User-Agent": "Mine/1.0"}
                )
    finally:
        requests.sessions.Session.request = original

    assert seen["headers"]["User-Agent"] == "Mine/1.0"


def test_the_patch_is_removed_afterwards():
    """It is scoped to the PyTDC call, not set globally."""
    import requests

    before = requests.sessions.Session.request
    with tdc_tool._requests_user_agent("TestAgent/9.9"):
        assert requests.sessions.Session.request is not before
    assert requests.sessions.Session.request is before


def test_the_patch_is_removed_even_when_the_call_raises():
    import requests

    before = requests.sessions.Session.request
    with pytest.raises(ValueError):
        with tdc_tool._requests_user_agent("TestAgent/9.9"):
            raise ValueError("boom")
    assert requests.sessions.Session.request is before


def test_the_default_user_agent_is_not_python_requests():
    """The one string Dataverse blocks."""
    assert "python-requests" not in tdc_tool._DATAVERSE_USER_AGENT
    assert tdc_tool._DATAVERSE_USER_AGENT.strip()


def test_a_pytdc_sys_exit_becomes_an_error_not_a_dead_process():
    """SystemExit is not an Exception, so it passed through every handler."""

    class FakeDataset:
        def __init__(self, name):
            raise SystemExit("Please report this error to contact@tdcommons.ai")

    tdc_tool.TDCDatasetTool._dataset_cache = {}

    import sys
    import types

    module = types.ModuleType("fake_tdc_problem")
    module.ADME = FakeDataset
    sys.modules["fake_tdc_problem"] = module
    try:
        with pytest.raises(tdc_tool.TDCDownloadAborted) as caught:
            tdc_tool.TDCDatasetTool._get_dataset(
                "fake_tdc_problem", "ADME", "Caco2_Wang"
            )
    finally:
        del sys.modules["fake_tdc_problem"]

    assert "Caco2_Wang" in str(caught.value)
    assert isinstance(caught.value, RuntimeError), (
        "it has to be catchable by the handlers that already exist"
    )
