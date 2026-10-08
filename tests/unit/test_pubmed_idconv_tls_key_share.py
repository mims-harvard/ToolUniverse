"""PubMed_convert_article_ids failed on current Python builds.

pmc.ncbi.nlm.nih.gov answers HTTP 403 to TLS handshakes that offer the
post-quantum hybrid key share OpenSSL 3.5 sends by default (the Python builds
uv installs, so a standard ``uvx tooluniverse``). The same request with only
classic groups gets 200. The tool now mounts an adapter that offers a classic
key share for that host only, and a non-JSON reply is reported with its HTTP
status instead of a JSON-decoder message.
"""

import ssl
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


def _tool():
    from tooluniverse.pubmed_utils_tool import PubMedConvertIDsTool

    return PubMedConvertIDsTool({"name": "PubMed_convert_article_ids"})


def test_pmc_host_uses_the_classic_key_share_adapter_and_other_hosts_do_not():
    from tooluniverse.pubmed_utils_tool import (
        ECITMATCH_URL,
        IDCONV_URL,
        _ClassicKeyShareAdapter,
    )

    session = _tool().session
    assert isinstance(session.get_adapter(IDCONV_URL), _ClassicKeyShareAdapter)
    assert not isinstance(session.get_adapter(ECITMATCH_URL), _ClassicKeyShareAdapter)


def test_adapter_hands_urllib3_a_restricted_ssl_context():
    from tooluniverse.pubmed_utils_tool import _ClassicKeyShareAdapter

    captured = {}
    with patch.object(ssl.SSLContext, "set_ecdh_curve", autospec=True) as curve:
        adapter = _ClassicKeyShareAdapter()
        captured.update(adapter.poolmanager.connection_pool_kw)
    curve.assert_called_once()
    assert curve.call_args.args[-1] == "prime256v1"
    assert isinstance(captured["ssl_context"], ssl.SSLContext)


def test_non_json_403_is_reported_with_its_status_not_a_decoder_message():
    response = MagicMock()
    response.status_code = 403
    response.text = "<!doctype html><title>403</title>403 Forbidden"
    response.json.side_effect = ValueError("Expecting value: line 1 column 1 (char 0)")

    with patch(
        "tooluniverse.pubmed_utils_tool.request_with_retry", return_value=response
    ):
        result = _tool().run({"ids": ["23193287"]})

    assert result["status"] == "error"
    assert "HTTP 403" in result["error"]
    assert "Expecting value" not in result["error"]


@pytest.mark.network
def test_live_conversion_succeeds():
    result = _tool().run({"ids": ["23193287"]})
    assert result["status"] == "success", result
    assert result["data"][0]["pmcid"] == "PMC3531190"
