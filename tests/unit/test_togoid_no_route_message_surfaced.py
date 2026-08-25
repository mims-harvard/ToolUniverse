"""Regression guard: TogoID reports an unroutable conversion as an HTTP 400
carrying a JSON body {"message": "no route: hgnc_symbol <> uniprot"}.

_togoid_get called resp.raise_for_status() before ever looking at the body, so
the RequestException handler discarded the server's explanation and the caller
got an opaque URL dump instead:

    TogoID request failed: 400 Client Error: Bad Request for url:
    https://api.togoid.dbcls.jp/convert?ids=TP53&route=hgnc_symbol%2Cuniprot...

which also made TogoIDConvertTool's deliberate "no route" guidance branch
unreachable. Confirmed live: the 2-step hgnc_symbol->uniprot route 400s with
that message, while the multi-hop hgnc_symbol,hgnc,uniprot route succeeds.

The fix reads the JSON body on an error response and surfaces its `message`,
falling back to the previous text when there is no parseable body.
"""

from unittest.mock import MagicMock, patch

import pytest
import requests

from tooluniverse.togoid_tool import TogoIDConvertTool, TogoIDDatasetsTool

pytestmark = pytest.mark.unit


def _cfg(name, typ):
    return {"name": name, "type": typ, "parameter": {"type": "object", "properties": {}}}


def _error_resp(status, json_body=None, http_error_text=""):
    """A response that raise_for_status() rejects, as requests would."""
    resp = MagicMock()
    resp.status_code = status
    if json_body is None:
        resp.json.side_effect = ValueError("Expecting value: line 1 column 1 (char 0)")
    else:
        resp.json.return_value = json_body
    resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
        http_error_text or f"{status} Error for url: https://api.togoid.dbcls.jp/convert"
    )
    return resp


def _convert_tool():
    return TogoIDConvertTool(_cfg("TogoID_convert", "TogoIDConvertTool"))


def test_no_route_400_surfaces_upstream_message():
    resp = _error_resp(400, {"message": "no route: hgnc_symbol <> uniprot"})

    with patch("tooluniverse.togoid_tool.requests.get", return_value=resp):
        out = _convert_tool().run(
            {"ids": "TP53", "source": "hgnc_symbol", "target": "uniprot"}
        )

    assert out["status"] == "error"
    error = out["error"]
    assert "no route" in error
    assert "hgnc_symbol" in error
    assert "uniprot" in error
    # Actionable guidance, not a bare URL dump.
    assert "directly related" in error
    assert "https://api.togoid.dbcls.jp" not in error


def test_non_json_500_still_produces_a_sane_error():
    resp = _error_resp(
        500,
        json_body=None,
        http_error_text="500 Server Error: Internal Server Error for url: "
        "https://api.togoid.dbcls.jp/convert",
    )

    with patch("tooluniverse.togoid_tool.requests.get", return_value=resp):
        out = _convert_tool().run(
            {"ids": "TP53", "source": "hgnc_symbol", "target": "uniprot"}
        )

    assert out["status"] == "error"
    assert "500" in out["error"]
    assert out["error"].strip()


def test_json_error_body_without_message_falls_back_to_http_text():
    resp = _error_resp(400, {"detail": "something else"}, "400 Client Error: Bad Request")

    with patch("tooluniverse.togoid_tool.requests.get", return_value=resp):
        out = _convert_tool().run(
            {"ids": "TP53", "source": "hgnc_symbol", "target": "uniprot"}
        )

    assert out["status"] == "error"
    assert "400" in out["error"]


def test_successful_convert_is_unaffected():
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status.return_value = None
    resp.json.return_value = {
        "ids": ["ENSG00000139618"],
        "results": ["P51587"],
        "route": ["ensembl_gene", "uniprot"],
    }

    with patch("tooluniverse.togoid_tool.requests.get", return_value=resp):
        out = _convert_tool().run(
            {"ids": "ENSG00000139618", "source": "ensembl_gene", "target": "uniprot"}
        )

    assert out["status"] == "success"
    assert out["data"]["converted_ids"] == ["P51587"]


def test_datasets_error_response_stays_an_error_not_an_empty_success():
    resp = _error_resp(400, {"message": "bad request"})

    with patch("tooluniverse.togoid_tool.requests.get", return_value=resp):
        out = TogoIDDatasetsTool(
            _cfg("TogoID_list_datasets", "TogoIDDatasetsTool")
        ).run({"category": "Gene"})

    assert out["status"] == "error"
    assert "bad request" in out["error"]
