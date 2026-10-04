"""The 429s were our concurrency, and the limiter already existed.

The weekly sweep runs 10 workers against live APIs. Several categories answered
429, and measured afterwards on their own, RNAcentral served eight rapid
requests without complaint -- so those 429s came from the worker pool, not from
a ceiling either tool crossed alone. DBLP was different: it answered 200 to
requests 1-3, 429 to the 4th, and then refused to connect at all, so an
over-eager client loses the endpoint rather than one call. EBI was different
again: by the end of the triage it answered 429 to the *first* request, which
is a sustained-use penalty earned across runs.

enforce_provider_rate_limit has been in the tree all along, shared by pubmed,
icite and medgen under the provider name "ncbi". Only semantic_scholar_ext
declared anything in config; every other tool that got throttled has a
dedicated class that never called it. These tests check the wiring, with an
injected clock, because a live API that has already penalised us cannot
demonstrate a fix.
"""

import importlib
from pathlib import Path

import pytest

from tooluniverse.provider_rate_limit import ProviderRateLimiter

pytestmark = pytest.mark.unit

SRC = Path(__file__).resolve().parents[2] / "src" / "tooluniverse"


class _Clock:
    """A clock that only moves when the limiter sleeps."""

    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


def test_a_shared_bucket_paces_requests():
    clock = _Clock()
    limiter = ProviderRateLimiter(clock=clock.time, sleep=clock.sleep)

    for _ in range(4):
        limiter.wait("dblp", "", 1.0)

    # The first goes straight through; each of the next three waits a second.
    assert len(clock.sleeps) == 3
    assert all(abs(s - 1.0) < 1e-6 for s in clock.sleeps)
    assert abs(clock.now - 3.0) < 1e-6


def test_two_callers_of_one_provider_share_the_budget():
    """This is what the sweep's workers were not doing."""
    clock = _Clock()
    limiter = ProviderRateLimiter(clock=clock.time, sleep=clock.sleep)

    limiter.wait("rnacentral", "", 3.0)
    limiter.wait("rnacentral", "", 3.0)

    assert len(clock.sleeps) == 1, (
        "a second caller must wait for the same bucket, or ten workers spend "
        "ten budgets"
    )


def test_separate_providers_do_not_block_each_other():
    clock = _Clock()
    limiter = ProviderRateLimiter(clock=clock.time, sleep=clock.sleep)

    limiter.wait("rnacentral", "", 3.0)
    limiter.wait("ebi", "", 3.0)

    assert clock.sleeps == []


def test_no_rate_means_no_wait():
    clock = _Clock()
    limiter = ProviderRateLimiter(clock=clock.time, sleep=clock.sleep)

    for _ in range(5):
        limiter.wait("somewhere", "", None)

    assert clock.sleeps == []


def test_clinvar_joins_the_bucket_pubmed_already_shares():
    """It called efetch with neither the key nor the bucket."""
    source = (SRC / "clinvar_submitted_tool.py").read_text("utf-8")

    assert 'enforce_provider_rate_limit("ncbi"' in source
    assert "10.0 if api_key else 3.0" in source, (
        "NCBI publishes X-Ratelimit-Limit: 3 without a key and 10 with one, "
        "and the other three NCBI tools already use those numbers"
    )
    assert 'self.credential("NCBI_API_KEY")' in source
    assert 'params["api_key"] = api_key' in source, (
        "the higher limit only applies if the key is actually sent"
    )


def test_dblp_is_paced_and_the_rate_is_justified():
    source = (SRC / "dblp_tool.py").read_text("utf-8")

    assert 'enforce_provider_rate_limit("dblp", "", 1.0)' in source
    assert "429" in source and "connect" in source, (
        "the comment should record what was measured, since DBLP publishes no "
        "rate-limit header to point at"
    )


@pytest.mark.parametrize("module", ["mirna_tool", "gwas_tool"])
def test_every_request_site_goes_through_the_limiter(module):
    """Five call sites each; patching one would have left four unpaced."""
    source = (SRC / f"{module}.py").read_text("utf-8")
    body = source.split("def _rate_limited_get", 1)[1]
    after_helper = body.split("\n\n", 2)[-1]

    assert "requests.get(" not in after_helper, (
        "a direct requests.get outside the helper is an unpaced call site"
    )
    assert "_rate_limited_get(" in after_helper
    assert "_HOST_RATE_LIMITS" in source


def test_the_host_table_picks_the_right_provider():
    """mirna_tool reads two different hosts and must not pool them."""
    mirna = importlib.import_module("tooluniverse.mirna_tool")
    table = dict((host, provider) for host, provider, _rps in mirna._HOST_RATE_LIMITS)

    assert table["rnacentral.org"] == "rnacentral"
    assert table["ebi.ac.uk"] == "ebi"


def test_an_unlisted_host_is_not_silently_blocked():
    """A URL the table does not know should still be fetched."""
    mirna = importlib.import_module("tooluniverse.mirna_tool")
    calls = []

    class _FakeRequests:
        @staticmethod
        def get(url, **kwargs):
            calls.append(url)
            return "ok"

    original = mirna.requests
    mirna.requests = _FakeRequests
    try:
        assert mirna._rate_limited_get("https://example.invalid/x") == "ok"
    finally:
        mirna.requests = original

    assert calls == ["https://example.invalid/x"]
