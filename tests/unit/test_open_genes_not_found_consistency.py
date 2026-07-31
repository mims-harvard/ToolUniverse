"""Regression guard for Fix-R30D-5: OpenGenesGeneTool's "gene not found"
outcome had two different response envelopes depending on how the upstream
API happened to signal it.

Confirmed live: an unknown symbol (e.g. FAKEGENE123) gets a genuine HTTP 404
from open-genes.com/api/gene/{symbol} with body
{"message": "Gene FAKEGENE123 not found", ...}. Before this fix, _fetch_json
let requests.raise_for_status() turn that into a hard requests.HTTPError,
caught by the generic RequestException handler and returned as
{"status": "error", ...} -- a different shape than the tool's own existing
handling for a 200-with-malformed-body response (which it already treated
gracefully as {"status": "success", "data": {}, "metadata": {"note": ...}}).
Both cases mean the same thing to a caller and now return the same shape.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.open_genes_tool import OpenGenesGeneTool, _fetch_json

pytestmark = pytest.mark.unit


def _tool():
    return OpenGenesGeneTool({"name": "opengenes_test", "fields": {}})


def _404_response():
    r = MagicMock()
    r.status_code = 404
    r.raise_for_status = MagicMock(
        side_effect=requests.exceptions.HTTPError("404 Client Error")
    )
    r.json.return_value = {"message": "Gene FAKEGENE123 not found", "status": 404}
    return r


class TestNotFoundEnvelopeConsistency:
    def test_404_response_treated_as_graceful_not_found(self):
        tool = _tool()
        with patch(
            "tooluniverse.open_genes_tool.requests.get", return_value=_404_response()
        ):
            result = tool.run({"symbol": "FAKEGENE123"})

        assert result["status"] == "success"
        assert result["data"] == {}
        assert "not in Open Genes" in result["metadata"]["note"]

    def test_real_network_failure_still_reports_as_error(self):
        tool = _tool()
        with patch(
            "tooluniverse.open_genes_tool.requests.get",
            side_effect=requests.exceptions.ConnectionError("boom"),
        ):
            result = tool.run({"symbol": "FOXO3"})

        assert result["status"] == "error"

    def test_fetch_json_not_found_ok_returns_none_on_404(self):
        with patch(
            "tooluniverse.open_genes_tool.requests.get", return_value=_404_response()
        ):
            result = _fetch_json("gene/FAKEGENE123", 30, not_found_ok=True)

        assert result is None

    def test_fetch_json_without_not_found_ok_still_errors_on_404(self):
        with patch(
            "tooluniverse.open_genes_tool.requests.get", return_value=_404_response()
        ):
            result = _fetch_json("gene/FAKEGENE123", 30)

        assert result["status"] == "error"
