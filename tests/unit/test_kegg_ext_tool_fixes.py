"""Regression guard for round-18 KEGG fixes (Fix-R18E-1 through R18E-7), all
confirmed live via raw curl against rest.kegg.jp:

- R18E-1: KEGG_get_drug's PATHWAY/DISEASE fields are nested 2 spaces under
  TARGET/EFFICACY (not top-level, 0-indent fields like every other field
  this parser recognized), so they -- and their continuation lines -- were
  silently dropped entirely (confirmed for D01441/imatinib: 3 real
  pathways, 7 real diseases, all lost).
- R18E-2: KEGG_get_disease uses the field name DIS_PATHWAY (not PATHWAY)
  for its pathway associations (confirmed for H00004/CML).
- R18E-4: KEGG_get_brite_hierarchy 404s uninformatively for "(table)"-type
  BRITE files that have no JSON representation upstream (confirmed for
  br08341, Pharmacogenomic biomarkers).
- R18E-5: KEGG_get_variant drops COSF (COSMIC Fusion) and OmimVar
  cross-refs -- the parser only recognized ClinVar/dbSNP/COSM keys
  (confirmed for hsa_var:25v1, BCR-ABL).
- R18E-6/7: KEGG_get_network 404s on a bare "nt######"-style network ID
  unless "network:" is prepended (confirmed for nt06276), and its child
  elements are listed under MEMBER (not ELEMENT) for that ID family
  (confirmed 9 real entries silently dropped).
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.kegg_ext_tool import KEGGExtTool

pytestmark = pytest.mark.unit


def _tool(endpoint):
    return KEGGExtTool({"name": "kegg_test", "fields": {"endpoint": endpoint}})


def _resp(text):
    r = MagicMock()
    r.text = text
    r.raise_for_status = MagicMock()
    return r


def _http_error(status_code):
    resp = MagicMock()
    resp.status_code = status_code
    return requests.exceptions.HTTPError(response=resp)


DRUG_FLAT_FILE = """ENTRY       D01441                      Drug
NAME        Imatinib mesylate (USAN)
FORMULA     C29H31N7O. CH4SO3
TARGET      BCR-ABL [HSA_VAR:25v1] [HSA:25] [KO:K06619]
            FIP1L1-PDGFRA [HSA:5156] [KO:K04363]
  PATHWAY   hsa04010(3815+5156)  MAPK signaling pathway
            hsa05200(25+3815+5156)  Pathways in cancer
            hsa05220(25)  Chronic myeloid leukemia
  NETWORK   nt06276  Chronic myeloid leukemia
EFFICACY    Antineoplastic, Tyrosine kinase inhibitor
  DISEASE   Chronic myeloid leukemia (Philadelphia chromosome positive) [DS:H00004]
            Acute lymphoblastic leukemia (Philadelphia chromosome positive) [DS:H00001]
///
"""

DISEASE_FLAT_FILE = """ENTRY       H00004                      Disease
NAME        Chronic myeloid leukemia
CATEGORY    Cancer
DIS_PATHWAY hsa05220  Chronic myeloid leukemia
NETWORK     nt06276 Chronic myeloid leukemia
///
"""

VARIANT_FLAT_FILE = """ENTRY       hsa_var:25v1
NAME        BCR-ABL
VARIATION   translocation t(9;22)(q34;q11)
            COSF: 1756 1758 1783
            mutation T315I
            OmimVar: 189980
///
"""

NETWORK_FLAT_FILE = """ENTRY       nt06276           Map       Network
NAME        Chronic myeloid leukemia
MEMBER      N00001  EGF-EGFR-RAS-ERK signaling pathway
            N00002  BCR-ABL fusion kinase to RAS-ERK signaling pathway
///
"""


def test_get_drug_captures_nested_pathway_and_disease():
    tool = _tool("get_drug")

    with patch(
        "tooluniverse.kegg_ext_tool.requests.get",
        return_value=_resp(DRUG_FLAT_FILE),
    ):
        result = tool._get_drug({"drug_id": "D01441"})

    data = result["data"]
    assert data["pathways"] == {
        "hsa04010(3815+5156)": "MAPK signaling pathway",
        "hsa05200(25+3815+5156)": "Pathways in cancer",
        "hsa05220(25)": "Chronic myeloid leukemia",
    }
    assert data["diseases"] == [
        "Chronic myeloid leukemia (Philadelphia chromosome positive) [DS:H00004]",
        "Acute lymphoblastic leukemia (Philadelphia chromosome positive) [DS:H00001]",
    ]
    # TARGET (top-level, 0-indent) still parses correctly alongside the
    # newly-recognized nested fields.
    assert len(data["targets"]) == 2


def test_get_disease_captures_dis_pathway_field():
    tool = _tool("get_disease")

    with patch(
        "tooluniverse.kegg_ext_tool.requests.get",
        return_value=_resp(DISEASE_FLAT_FILE),
    ):
        result = tool._get_disease({"disease_id": "H00004"})

    assert result["data"]["pathways"] == {"hsa05220": "Chronic myeloid leukemia"}


def test_get_variant_captures_cosf_and_omimvar():
    tool = _tool("get_variant")

    with patch(
        "tooluniverse.kegg_ext_tool.requests.get",
        return_value=_resp(VARIANT_FLAT_FILE),
    ):
        result = tool._get_variant({"variant_id": "hsa_var:25v1"})

    variations = result["data"]["variations"]
    assert variations[0]["mutation"] == "translocation t(9;22)(q34;q11)"
    assert variations[0]["cosmic_fusion"] == ["1756", "1758", "1783"]
    assert variations[1]["mutation"] == "T315I"
    assert variations[1]["omim_variant"] == ["189980"]


def test_get_network_prepends_network_prefix_for_nt_ids():
    tool = _tool("get_network")
    captured = {}

    def fake_get(url, **kwargs):
        captured["url"] = url
        return _resp(NETWORK_FLAT_FILE)

    with patch("tooluniverse.kegg_ext_tool.requests.get", side_effect=fake_get):
        result = tool._get_network({"network_id": "nt06276"})

    assert captured["url"].endswith("/get/network:nt06276")
    assert result["data"]["elements"] == [
        "N00001  EGF-EGFR-RAS-ERK signaling pathway",
        "N00002  BCR-ABL fusion kinase to RAS-ERK signaling pathway",
    ]
    # The output still reports the caller's original (unprefixed) ID.
    assert result["data"]["network_id"] == "nt06276"


def test_get_network_does_not_prefix_n_style_ids():
    tool = _tool("get_network")
    captured = {}

    def fake_get(url, **kwargs):
        captured["url"] = url
        return _resp("ENTRY       N00001\nNAME        Test\n///\n")

    with patch("tooluniverse.kegg_ext_tool.requests.get", side_effect=fake_get):
        tool._get_network({"network_id": "N00001"})

    assert captured["url"].endswith("/get/N00001")


def test_get_network_does_not_double_prefix_already_prefixed_id():
    tool = _tool("get_network")
    captured = {}

    def fake_get(url, **kwargs):
        captured["url"] = url
        return _resp(NETWORK_FLAT_FILE)

    with patch("tooluniverse.kegg_ext_tool.requests.get", side_effect=fake_get):
        tool._get_network({"network_id": "network:nt06276"})

    assert captured["url"].endswith("/get/network:nt06276")
    assert "network:network:" not in captured["url"]


def test_brite_hierarchy_404_gives_table_type_hint():
    tool = _tool("get_brite_hierarchy")

    def fake_get(*a, **k):
        raise _http_error(404)

    with patch("tooluniverse.kegg_ext_tool.requests.get", side_effect=fake_get):
        result = tool.run({"hierarchy_id": "br08341"})

    assert result["status"] == "error"
    assert "br08341" in result["error"]
    assert "table-type" in result["error"]


def test_other_endpoint_404_keeps_generic_message():
    tool = _tool("get_drug")

    def fake_get(*a, **k):
        raise _http_error(404)

    with patch("tooluniverse.kegg_ext_tool.requests.get", side_effect=fake_get):
        result = tool.run({"drug_id": "D99999"})

    assert result["status"] == "error"
    assert result["error"] == "KEGG entry not found"
