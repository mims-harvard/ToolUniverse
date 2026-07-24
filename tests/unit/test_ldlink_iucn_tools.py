"""LDlink (LD proxies) and IUCN (conservation status) key-gated tools.

Both fill real skill gaps (gwas-snp-interpretation needs LD context; ecology
needs Red List status) via free-token APIs. Tests cover the no-token guard and
the response parsing (with the token mocked).
"""

import os
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


def _ldlink(token=""):
    from tooluniverse.ldlink_tool import LDlinkTool

    t = LDlinkTool({"name": "LDlink_get_proxies", "type": "LDlinkTool"})
    t.token = token
    return t


def test_ldlink_no_token_guides_registration():
    t = _ldlink("")
    r = t.run({"variant": "rs7903146"})
    assert r["status"] == "error"
    assert "LDLINK_TOKEN" in r["error"] and "register" in r["error"].lower()


def test_ldlink_parses_and_filters_by_r2():
    t = _ldlink("TOKEN")
    tsv = (
        "RS_Number\tCoord\tAlleles\tMAF\tDistance\tDprime\tR2\tCorrelated_Alleles\tFORGEdb\tRegulomeDB\tFunction\n"
        "rs7903146\tchr10:112998590\t(C/T)\t0.3\t0\t1.0\t1.0\t\t\t\t\n"
        "rs4506565\tchr10:112998930\t(T/A)\t0.3\t340\t1.0\t0.92\t\t\t\t\n"
        "rs_lowLD\tchr10:113000000\t(A/G)\t0.1\t9999\t0.5\t0.40\t\t\t\t\n"
    )
    resp = MagicMock()
    resp.status_code = 200
    resp.text = tsv
    with patch("tooluniverse.ldlink_tool.requests.get", return_value=resp) as get:
        r = t.run({"variant": "rs7903146", "r2_threshold": 0.8})
    assert get.call_args.kwargs["params"]["var"] == "rs7903146"
    assert r["status"] == "success"
    rsids = [p["rsid"] for p in r["data"]]
    assert "rs4506565" in rsids and "rs_lowLD" not in rsids  # R2<0.8 filtered
    assert r["data"][0]["r2"] == 1.0  # ranked by R2


def _iucn(token=""):
    from tooluniverse.iucn_tool import IUCNTool

    t = IUCNTool({"name": "IUCN_get_conservation_status", "type": "IUCNTool"})
    t.token = token
    return t


def test_iucn_no_token_guides_registration():
    t = _iucn("")
    r = t.run({"scientific_name": "Panthera leo"})
    assert r["status"] == "error"
    assert "IUCN_API_KEY" in r["error"]


def test_iucn_parses_category_and_splits_name():
    t = _iucn("TOKEN")
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "assessments": [
            {"red_list_category_code": "VU", "year_published": "2014", "latest": False, "assessment_id": 1},
            {"red_list_category_code": "EN", "year_published": "2023", "latest": True, "assessment_id": 2},
        ]
    }
    with patch("tooluniverse.iucn_tool.requests.get", return_value=resp) as get:
        r = t.run({"scientific_name": "Panthera leo"})
    params = get.call_args.kwargs["params"]
    assert params["genus_name"] == "Panthera" and params["species_name"] == "leo"
    assert r["status"] == "success"
    assert r["data"]["red_list_category_code"] == "EN"
    assert r["data"]["red_list_category"] == "Endangered"


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
