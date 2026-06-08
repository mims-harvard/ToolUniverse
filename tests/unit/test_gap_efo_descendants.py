"""Unit tests for ols_get_efo_term_descendants (OLSRESTTool kind='descendants').

Closes the gap where TU exposed direct EFO CHILDREN but not the transitive
DESCENDANTS (full subtree). The descendants endpoint is the symmetric
.../{double-encoded-iri}/descendants?size=N on OLS4.

All HTTP is mocked; no network access required.
"""

from unittest.mock import MagicMock, patch

from tooluniverse.efo_tool import OLSRESTTool


DESCENDANTS_CONFIG = {
    "name": "ols_get_efo_term_descendants",
    "type": "OLSRESTTool",
    "fields": {"kind": "descendants", "ontology_id": "efo"},
}


def _make_tool():
    return OLSRESTTool(DESCENDANTS_CONFIG)


def _ok_response(url, payload):
    resp = MagicMock()
    resp.status_code = 200
    resp.url = url
    resp.json.return_value = payload
    return resp


def test_double_url_encoding_in_descendants_url():
    """The term IRI must be DOUBLE URL-encoded and hit the /descendants path."""
    captured = {}

    def fake_request(_req, _method, url, params=None, timeout=None):
        captured["url"] = url
        captured["params"] = params
        return _ok_response(url, {"_embedded": {"terms": []}, "page": {"totalElements": 0}})

    with patch("tooluniverse.efo_tool.request_with_retry", side_effect=fake_request):
        tool = _make_tool()
        tool.run({"obo_id": "EFO:0001444", "size": 5})

    # EFO:0001444 -> http://www.ebi.ac.uk/efo/EFO_0001444, then double-encoded.
    # Single-encode of "://" is "%3A%2F%2F"; double-encode is "%253A%252F%252F".
    assert "/ontologies/efo/terms/" in captured["url"]
    assert captured["url"].endswith("/descendants")
    assert "%253A%252F%252F" in captured["url"]
    assert "EFO_0001444" in captured["url"]
    assert captured["params"] == {"size": 5}


def test_embedded_terms_parsed_into_rows():
    """_embedded.terms[] entries become {iri, obo_id, short_form, label} rows."""
    payload = {
        "_embedded": {
            "terms": [
                {
                    "iri": "http://purl.obolibrary.org/obo/GO_0072718",
                    "obo_id": "GO:0072718",
                    "short_form": "GO_0072718",
                    "label": "response to cisplatin",
                },
                {
                    "iri": "http://purl.obolibrary.org/obo/HP_0001522",
                    "obo_id": "HP:0001522",
                    "short_form": "HP_0001522",
                    "label": "Death in infancy",
                },
            ]
        },
        "page": {"totalElements": 25021},
    }

    def fake_request(_req, _method, url, params=None, timeout=None):
        return _ok_response(url + "?size=2", payload)

    with patch("tooluniverse.efo_tool.request_with_retry", side_effect=fake_request):
        tool = _make_tool()
        result = tool.run({"obo_id": "EFO:0001444", "size": 2})

    assert result["status"] == "success"
    data = result["data"]
    assert data["count"] == 2
    rows = data["descendants"]
    assert rows[0]["obo_id"] == "GO:0072718"
    assert rows[0]["label"] == "response to cisplatin"
    assert rows[1]["short_form"] == "HP_0001522"
    # Children tool keys must NOT leak in; this is descendants.
    assert "children" not in data


def test_total_extracted_from_page_total_elements():
    """The full subtree size comes from page.totalElements, not len(rows)."""
    payload = {
        "_embedded": {"terms": [{"iri": "x", "obo_id": "EFO:1", "label": "a"}]},
        "page": {"totalElements": 25021},
    }

    def fake_request(_req, _method, url, params=None, timeout=None):
        return _ok_response(url, payload)

    with patch("tooluniverse.efo_tool.request_with_retry", side_effect=fake_request):
        tool = _make_tool()
        result = tool.run({"obo_id": "EFO:0001444", "size": 1})

    data = result["data"]
    assert data["total"] == 25021
    assert data["count"] == 1  # only one row returned despite large total


def test_missing_page_total_is_none():
    """When page.totalElements is absent, total is None (not an exception)."""
    payload = {"_embedded": {"terms": []}}

    def fake_request(_req, _method, url, params=None, timeout=None):
        return _ok_response(url, payload)

    with patch("tooluniverse.efo_tool.request_with_retry", side_effect=fake_request):
        tool = _make_tool()
        result = tool.run({"iri": "http://www.ebi.ac.uk/efo/EFO_0001444"})

    data = result["data"]
    assert data["total"] is None
    assert data["count"] == 0
    assert data["descendants"] == []


def test_http_error_returns_error_envelope():
    """A non-2xx response yields a structured error, not a success."""

    def fake_request(_req, _method, url, params=None, timeout=None):
        resp = MagicMock()
        resp.status_code = 404
        resp.url = url
        resp.text = "Not Found"
        return resp

    with patch("tooluniverse.efo_tool.request_with_retry", side_effect=fake_request):
        tool = _make_tool()
        result = tool.run({"obo_id": "EFO:0001444", "size": 5})

    assert result["status"] == "error"
    assert result["status_code"] == 404
    assert "HTTP request failed" in result["error"]


def test_requires_iri_or_obo_id():
    """Neither iri nor obo_id provided -> actionable error, no HTTP call."""
    with patch("tooluniverse.efo_tool.request_with_retry") as m:
        tool = _make_tool()
        result = tool.run({"size": 5})

    assert result["status"] == "error"
    assert "iri" in result["error"] and "obo_id" in result["error"]
    m.assert_not_called()
