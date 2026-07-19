"""Regression guard for Fix-R21A-2: PubChemToxTool's name->CID resolution
failure and its per-heading "no data" failure were both surfaced as the
identical, misleading "No toxicity data found in PubChem for: X. This
heading may not exist for this compound." message.

Confirmed live: PubChem's own /pug/compound/name/{name}/cids/JSON endpoint
returns HTTP 404 for a name that doesn't resolve at all, not just an empty
CID list. That 404 was propagating out of _resolve_cid() as a generic
requests.HTTPError, indistinguishable from a 404 on the actual toxicity
PUG View lookup for a real, resolved compound missing a specific heading
(e.g. caffeine has no "Target Organs" heading). A toxicologist debugging a
typo would be misled into thinking the compound resolved fine. Fixed by
checking status_code==404 inside _resolve_cid() and raising a distinct,
clear ValueError before it reaches the generic HTTPError(404) handler.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.pubchem_tox_tool import PubChemToxTool

pytestmark = pytest.mark.unit


def _tool():
    return PubChemToxTool({"name": "pubchem_tox_test", "fields": {"endpoint": "target_organs"}})


def _resp(status_code, json_body=None):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_body or {}
    return r


def test_nonexistent_compound_name_gives_distinct_error():
    tool = _tool()

    def fake_get(url, timeout=None, **kwargs):
        if "/cids/JSON" in url:
            return _resp(404)
        raise AssertionError("should not reach the PUG View lookup")

    with patch("tooluniverse.pubchem_tox_tool.requests.get", side_effect=fake_get):
        result = tool.run({"compound_name": "Zzznonexistentdrugxyz123"})

    assert result["status"] == "error"
    assert "No compound found for name" in result["error"]
    assert "This heading may not exist" not in result["error"]


def test_resolved_compound_missing_heading_gives_original_message():
    tool = _tool()

    def fake_get(url, timeout=None, **kwargs):
        if "/cids/JSON" in url:
            return _resp(200, {"IdentifierList": {"CID": [2519]}})
        # PUG View heading lookup 404s for a real, resolved compound.
        r = MagicMock()
        r.status_code = 404
        import requests

        r.raise_for_status = MagicMock(
            side_effect=requests.exceptions.HTTPError(response=r)
        )
        return r

    with patch("tooluniverse.pubchem_tox_tool.requests.get", side_effect=fake_get):
        result = tool.run({"compound_name": "caffeine"})

    assert result["status"] == "error"
    assert "This heading may not exist for this compound" in result["error"]
    assert "No compound found for name" not in result["error"]


def test_valid_compound_with_data_unaffected():
    tool = _tool()
    pug_view_body = {
        "Record": {
            "Section": [
                {
                    "TOCHeading": "Toxicity",
                    "Section": [
                        {
                            "TOCHeading": "Target Organs",
                            "Information": [
                                {
                                    "Value": {
                                        "StringWithMarkup": [{"String": "Liver, kidneys"}]
                                    }
                                }
                            ],
                        }
                    ],
                }
            ]
        }
    }

    def fake_get(url, timeout=None, **kwargs):
        if "/cids/JSON" in url:
            return _resp(200, {"IdentifierList": {"CID": [5359596]}})
        return _resp(200, pug_view_body)

    with patch("tooluniverse.pubchem_tox_tool.requests.get", side_effect=fake_get):
        result = tool.run({"compound_name": "arsenic"})

    assert result["status"] == "success"
    assert result["data"]["cid"] == 5359596
