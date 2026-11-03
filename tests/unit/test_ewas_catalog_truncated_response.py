"""The EWAS Catalog cannot deliver its largest gene payloads; say so.

Two upstream facts, both measured 2026-11-01:

* The catalogue is HTTPS-only. ``http://ewascatalog.org/api/?cpg=...`` answers
  404, which is why every EWAS Catalog call failed, and the 503 recorded on
  2026-10-09 is gone.
* For gene=AHRR the server announces ``Content-Length: 2751412`` and then closes
  the connection after 1.57-1.85 MB -- at a different offset on each of five
  attempts, plain and gzip alike. ``requests`` raises ``ChunkedEncodingError``
  and the JSON is always unterminated, so no client can recover that body.

The second used to surface as "Error querying EWAS Catalog: ('Connection
broken: IncompleteRead(1773027 bytes read, 978385 more expected)', ...)", which
reads like a transport blip worth retrying. It is not: it is a payload the
server will not serve. The tool now names the fault and points at the query
shape that works.
"""

import pytest
import requests

pytestmark = pytest.mark.unit


def _tool(operation):
    from tooluniverse.ewas_catalog_tool import EWASCatalogTool

    return EWASCatalogTool(
        {"name": f"t_{operation}", "fields": {"operation": operation}}
    )


def test_catalog_url_is_https():
    """The http:// form answers 404; the module must not point at it."""
    from tooluniverse.ewas_catalog_tool import EWAS_CATALOG_URL

    assert EWAS_CATALOG_URL.startswith("https://")


def test_truncated_body_is_reported_as_an_upstream_fault(monkeypatch):
    tool = _tool("search_by_gene")

    def _boom(*args, **kwargs):
        raise requests.exceptions.ChunkedEncodingError(
            "Connection broken: IncompleteRead(1773027 bytes read, "
            "978385 more expected)"
        )

    monkeypatch.setattr(requests, "get", _boom)
    out = tool.run({"gene_symbol": "AHRR", "limit": 5})

    assert out["status"] == "error"
    error = out["error"]
    # Names the fault, not a parse failure, and does not invite a retry.
    assert "closed the connection" in error
    assert "retrying does not clear" in error
    # Points at the query shape that does work.
    assert "search_by_cpg" in error
    # Keeps the diagnostic the caller needs to recognise it again.
    assert "IncompleteRead" in error


def test_other_connection_errors_keep_their_own_message(monkeypatch):
    """A real network failure must not be reported as upstream truncation."""
    tool = _tool("search_by_gene")

    def _boom(*args, **kwargs):
        raise requests.exceptions.ConnectionError("no route to host")

    monkeypatch.setattr(requests, "get", _boom)
    out = tool.run({"gene_symbol": "TP53"})

    assert out["status"] == "error"
    assert "Failed to connect" in out["error"]
    assert "closed the connection" not in out["error"]
