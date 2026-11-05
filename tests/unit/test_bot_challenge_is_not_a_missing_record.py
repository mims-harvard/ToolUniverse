"""A wall in front of the data must not be reported as data that is not there.

Three services answer this client with an interstitial instead of the record,
each measured live on 2026-11-05, and each was being described to the caller
as something else:

    ngdc.cncb.ac.cn/gsa   HTTP 200, ~1 KB, <title>SecurityCheck</title>,
                          "Verifying your browser, please wait..."
                          -> "No GSA accession found for 'CRA002926'."
                             CRA002926 exists; /gsa/browse/CRA002926 is 200.
    dblp.org  (publ)      HTTP 202, 7.4 KB Anubis proof-of-work page,
                          "Making sure you're not a bot!"
                          -> "DBLP API error 202"
    dblp.org  (author,    the same 202 page, through BaseRESTTool
               venue)     -> "server returned an HTML page instead of data.
                              The requested resource may not exist."

The difference matters because the two readings lead somewhere different: a
missing record or a bad parameter is the caller's to fix, and a wall is not --
there is nothing to correct in the query, and the answer is to use another
source. GSA's own code had the right message already and stopped reaching it
when GSA translated the page out of Chinese; DBLP's had the right message too,
in a branch that a 202 can never enter.

Nothing here attempts to pass a challenge. The tests pin what is *said* about
one.
"""

import pytest

from tooluniverse.http_utils import bot_challenge

# Real bodies, trimmed. Kept as literals so a test failure says what the page
# looked like rather than depending on the network.
ANUBIS_202 = (
    "<html><head><title>Making sure you're not a bot!</title></head><body>"
    '<div class="centered-div"><h1>Making sure you\'re not a bot!</h1>'
    '<script id="anubis_challenge" type="application/json">'
    '{"rules":{"algorithm":"fast","difficulty":16},"challenge":'
    '{"id":"01a1a9c4-c3de-7ec2-a62a-26b5dcf5e8f2"}}</script></div></body></html>'
)
GSA_SECURITYCHECK_EN = (
    '<!DOCTYPE html><html><head><meta charset="UTF-8">'
    '<title>SecurityCheck</title></head><body><div class="spinner"></div>'
    "<h2>Verifying your browser, please wait...</h2><script>"
    'document.cookie = "auth_token=" + token; setTimeout(function() '
    "{ window.location.reload(); }, 1000);</script></body></html>"
)
GSA_SECURITYCHECK_ZH = (
    "<!DOCTYPE html><html><head><title>正在进行安全检查"
    "</title></head><body><h2>正在验证您的浏览器"
    "</h2></body></html>"
)
ORDINARY_404_HTML = (
    "<html><head><title>404 Not Found</title></head>"
    "<body><h1>Not Found</h1></body></html>"
)


class _Resp:
    """The three attributes every detector here reads."""

    def __init__(self, status_code=200, text="", headers=None):
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}
        self.reason = ""


@pytest.mark.parametrize(
    "label,resp",
    [
        ("anubis 202", _Resp(202, ANUBIS_202)),
        ("gsa english 200", _Resp(200, GSA_SECURITYCHECK_EN)),
        ("gsa chinese 200", _Resp(200, GSA_SECURITYCHECK_ZH)),
        (
            "cloudflare 403",
            _Resp(403, "Just a moment...", {"cf-mitigated": "challenge"}),
        ),
    ],
)
def test_a_challenge_is_recognised(label, resp):
    msg = bot_challenge(resp)
    assert msg, label
    assert "does not mean the record is missing" in msg or "challenge" in msg


@pytest.mark.parametrize(
    "label,resp",
    [
        ("a real 404 page", _Resp(404, ORDINARY_404_HTML)),
        ("actual json", _Resp(200, '{"result": {"hits": {"hit": []}}}')),
        ("empty body", _Resp(200, "")),
        ("no response at all", None),
    ],
)
def test_ordinary_responses_are_not_called_a_challenge(label, resp):
    assert bot_challenge(resp) is None, label


def test_the_challenge_is_language_independent():
    """GSA translated its own wall; a one-language marker list goes stale."""
    assert bot_challenge(_Resp(200, GSA_SECURITYCHECK_EN))
    assert bot_challenge(_Resp(200, GSA_SECURITYCHECK_ZH))


def test_gsa_does_not_call_a_walled_record_missing():
    from tooluniverse.gsa_tool import _is_browser_check

    assert _is_browser_check(GSA_SECURITYCHECK_EN), (
        "the English SecurityCheck page must be recognised; when it was not, "
        "GSA_get_accession answered 'No GSA accession found for CRA002926' "
        "for an accession that exists"
    )
    assert _is_browser_check(GSA_SECURITYCHECK_ZH)
    assert not _is_browser_check(ORDINARY_404_HTML)


def test_dblp_names_the_wall_rather_than_the_status(monkeypatch):
    """A 202 must not be reported as a bare "DBLP API error 202"."""
    from tooluniverse import dblp_tool

    monkeypatch.setattr(
        dblp_tool, "enforce_provider_rate_limit", lambda *a, **k: None, raising=False
    )
    monkeypatch.setattr(
        dblp_tool.requests, "get", lambda *a, **k: _Resp(202, ANUBIS_202)
    )
    tool = dblp_tool.DBLPTool(
        {"name": "DBLP_search_publications", "fields": {}, "parameter": {}}
    )
    out = tool._search("deep learning", 2, 0)

    assert out["status"] == "error"
    assert "DBLP API error 202" != out["error"]
    assert "bot check" in out["error"] or "browser" in out["error"]
    assert "openalex_search_works" in out.get("reason", "")
