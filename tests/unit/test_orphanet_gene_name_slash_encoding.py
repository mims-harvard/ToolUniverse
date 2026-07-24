"""Regression guard for Fix-R30D-2: OrphanetTool's gene-disease lookup
silently returned 0 diseases for any gene whose full name contains a
literal "/" (e.g. "lamin A/C" for LMNA, which has 21 curated Orphanet
disease associations including Hutchinson-Gilford progeria syndrome).

Confirmed live against the real Orphadata API:
  - urllib.parse.quote("lamin A/C", safe="") -> "lamin%20A%2FC" -> 404
  - "lamin A-C" (slash replaced with a hyphen before encoding) -> 200, with
    all 21 real disease associations.
Orphadata's router doesn't decode a percent-encoded slash (%2F) back to "/"
before matching the path segment, so the correctly-encoded form 404s.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.orphanet_tool import OrphanetTool, _encode_orphadata_gene_name

pytestmark = pytest.mark.unit


def _tool():
    return OrphanetTool({"name": "orphanet_test"})


def _resp(status_code, json_body=None):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_body or {}
    if status_code >= 400:
        import requests

        r.raise_for_status.side_effect = requests.exceptions.HTTPError(response=r)
    else:
        r.raise_for_status = MagicMock()
    return r


class TestOrphadataGeneNameEncoding:
    def test_slash_replaced_with_hyphen_not_percent_encoded(self):
        assert _encode_orphadata_gene_name("lamin A/C") == "lamin%20A-C"

    def test_names_without_slash_unaffected(self):
        assert _encode_orphadata_gene_name("fibrillin 1") == "fibrillin%201"


class TestGetGeneDiseasesWithSlashInName:
    def test_symbol_resolving_to_slash_name_finds_diseases(self):
        tool = _tool()
        gene_list_resp = _resp(
            200,
            {
                "data": {
                    "results": [
                        {"symbol": "LMNA", "name": "lamin A/C"},
                    ]
                }
            },
        )
        diseases_resp = _resp(
            200,
            {
                "data": {
                    "results": [
                        {
                            "ORPHAcode": 740,
                            "Preferred term": "Hutchinson-Gilford progeria syndrome",
                        }
                    ]
                    * 21
                }
            },
        )

        captured_urls = []

        def fake_get(url, **kwargs):
            captured_urls.append(url)
            if "genes/names/lamin%20A%2FC" in url:
                return _resp(404)
            if "genes/names/lamin%20A-C" in url:
                return diseases_resp
            if url.endswith("genes?page=1"):
                return gene_list_resp
            return _resp(404)

        with patch("tooluniverse.orphanet_tool.requests.get", side_effect=fake_get):
            result = tool.run({"operation": "get_gene_diseases", "gene_symbol": "LMNA"})

        assert result["status"] == "success"
        assert result["data"]["disease_count"] == 21
        # The first attempt uses the un-mangled percent-encoded slash and
        # 404s (matching live behavior); the retry uses the hyphen form.
        assert any("lamin%20A-C" in u for u in captured_urls)
