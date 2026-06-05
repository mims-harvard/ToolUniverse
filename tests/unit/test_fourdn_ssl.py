"""FourDN tool returns an actionable message when 4DN serves an expired cert.

Regression: the 4DN Data Portal periodically presents an expired TLS
certificate (a server-side lapse). The tool used to leak the raw
`HTTPSConnectionPool ... SSLCertVerificationError` traceback as its error
string. It should instead explain the failure is a transient 4DN
infrastructure issue, not a malformed query -- without ever disabling cert
verification.
"""

import unittest
from unittest.mock import patch

import requests
import pytest

pytestmark = pytest.mark.unit


def _tool():
    from tooluniverse.fourdn_tool import FourDNTool

    return FourDNTool({"name": "FourDN_search_data", "type": "FourDNTool"})


class TestFourDNSSL(unittest.TestCase):
    def test_expired_cert_gives_actionable_message(self):
        tool = _tool()
        ssl_err = requests.exceptions.SSLError(
            "HTTPSConnectionPool(host='data.4dnucleome.org', port=443): "
            "Max retries exceeded (Caused by SSLError(SSLCertVerificationError("
            "1, '[SSL: CERTIFICATE_VERIFY_FAILED] certificate has expired')))"
        )
        with patch("tooluniverse.fourdn_tool.requests.get", side_effect=ssl_err):
            result = tool.run(
                {"operation": "search", "query": "Hi-C", "item_type": "File"}
            )
        self.assertEqual(result["status"], "error")
        err = result["data"]["error"]
        self.assertIn("4DN", err)
        self.assertIn("certificate", err.lower())
        # the raw connection-pool noise must not leak through
        self.assertNotIn("HTTPSConnectionPool", err)

    def test_non_ssl_error_passes_through(self):
        tool = _tool()
        with patch(
            "tooluniverse.fourdn_tool.requests.get",
            side_effect=requests.exceptions.Timeout("timed out"),
        ):
            result = tool.run(
                {"operation": "search", "query": "Hi-C", "item_type": "File"}
            )
        self.assertEqual(result["status"], "error")
        self.assertIn("timed out", result["data"]["error"])


if __name__ == "__main__":
    unittest.main()
