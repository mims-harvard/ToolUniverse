"""Unit tests for the metabolic-pathways-deep coverage tools.

Covers the five new tools that reuse existing tool classes:
  - BiGG_download_model          (BiGGModelsTool.download_model)
  - KEGG_get_module              (KEGGExtTool.get_module)
  - KEGG_get_reaction            (KEGGExtTool.get_reaction)
  - KEGG_get_enzyme              (KEGGExtTool.get_enzyme)
  - WikiPathways_get_pathway_metabolites (WikiPathwaysExtTool.get_pathway_metabolites)

Each tool has a parse test (mocked HTTP returning a realistic payload) and an
error-path test (HTTP failure / missing input -> {status: error} with no raise).
"""

import io
import json
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.bigg_models_tool import BiGGModelsTool
from tooluniverse.kegg_ext_tool import KEGGExtTool
from tooluniverse.wikipathways_ext_tool import WikiPathwaysExtTool

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _resp(status_code=200, *, json_data=None, text=""):
    r = MagicMock()
    r.status_code = status_code
    r.text = text if text else (json.dumps(json_data) if json_data else "")
    r.content = r.text.encode("utf-8")
    if json_data is not None:
        r.json.return_value = json_data
    else:
        r.json.side_effect = ValueError("no json")
    return r


def _bigg_tool():
    return BiGGModelsTool(
        {
            "name": "BiGG_download_model",
            "type": "BiGGModelsTool",
            "parameter": {"type": "object", "properties": {}, "required": []},
        }
    )


def _kegg_tool(endpoint):
    return KEGGExtTool(
        {
            "name": f"KEGG_{endpoint}",
            "type": "KEGGExtTool",
            "fields": {"endpoint": endpoint},
            "parameter": {"type": "object", "properties": {}},
        }
    )


def _wp_tool(endpoint):
    return WikiPathwaysExtTool(
        {
            "name": f"WikiPathways_{endpoint}",
            "type": "WikiPathwaysExtTool",
            "fields": {"endpoint": endpoint},
            "parameter": {"type": "object", "properties": {}},
        }
    )


# --------------------------------------------------------------------------- #
# BiGG_download_model
# --------------------------------------------------------------------------- #
_BIGG_MODEL = {
    "id": "e_coli_core",
    "version": "1",
    "compartments": {"c": "cytosol", "e": "extracellular space"},
    "genes": [{"id": "b0001"}, {"id": "b0002"}],
    "metabolites": [
        {"id": "glc__D_e", "compartment": "e"},
        {"id": "pyr_c", "compartment": "c"},
    ],
    "reactions": [
        {
            "id": "PFK",
            "lower_bound": 0.0,
            "upper_bound": 1000.0,
            "objective_coefficient": 0,
            "metabolites": {"f6p_c": -1.0, "fdp_c": 1.0},
        },
        {
            "id": "BIOMASS_Ecoli_core_w_GAM",
            "lower_bound": 0.0,
            "upper_bound": 1000.0,
            "objective_coefficient": 1,
            "metabolites": {"pyr_c": -1.0},
        },
    ],
}


def test_bigg_download_model_json_parse():
    """Parse a COBRA JSON model: counts, flux bounds, and objective reaction."""
    tool = _bigg_tool()
    with patch(
        "tooluniverse.bigg_models_tool.requests.get",
        return_value=_resp(200, json_data=_BIGG_MODEL),
    ):
        out = tool.run({"operation": "download_model", "model_id": "e_coli_core"})
    assert out["status"] == "success"
    data = out["data"]
    assert data["format"] == "json"
    assert data["reaction_count"] == 2
    assert data["metabolite_count"] == 2
    assert data["gene_count"] == 2
    # FBA-ready: flux bounds present and objective reaction detected.
    pfk = [r for r in data["model"]["reactions"] if r["id"] == "PFK"][0]
    assert pfk["lower_bound"] == 0.0 and pfk["upper_bound"] == 1000.0
    assert data["objective_reactions"] == ["BIOMASS_Ecoli_core_w_GAM"]
    assert data["compartments"]["c"] == "cytosol"


def test_bigg_download_model_sbml_parse():
    """format='sbml' returns the raw SBML text."""
    tool = _bigg_tool()
    sbml = "<?xml version='1.0'?><sbml></sbml>"
    with patch(
        "tooluniverse.bigg_models_tool.requests.get",
        return_value=_resp(200, text=sbml),
    ):
        out = tool.run(
            {"operation": "download_model", "model_id": "e_coli_core", "format": "sbml"}
        )
    assert out["status"] == "success"
    assert out["data"]["format"] == "sbml"
    assert out["data"]["sbml"] == sbml


def test_bigg_download_model_missing_id():
    """Missing model_id returns an error without raising."""
    tool = _bigg_tool()
    out = tool.run({"operation": "download_model"})
    assert out["status"] == "error"
    assert "model_id" in out["data"]["error"]


def test_bigg_download_model_404():
    """A 404 from BiGG returns a not-found error."""
    tool = _bigg_tool()
    with patch(
        "tooluniverse.bigg_models_tool.requests.get",
        return_value=_resp(404, text="Not Found"),
    ):
        out = tool.run({"operation": "download_model", "model_id": "bogus_model"})
    assert out["status"] == "error"
    assert "not found" in out["data"]["error"].lower()


# --------------------------------------------------------------------------- #
# KEGG_get_module
# --------------------------------------------------------------------------- #
_MODULE_TEXT = """ENTRY       M00001            Pathway   Module
NAME        Glycolysis (Embden-Meyerhof pathway), glucose => pyruvate
DEFINITION  (K00844,K12407,K00845) (K01810,K06859) K01803
CLASS       Pathway modules; Carbohydrate metabolism; Central carbohydrate metabolism
PATHWAY     map00010  Glycolysis / Gluconeogenesis
            map01200  Carbon metabolism
REACTION    R00299  C00267 -> C00668
            R00756  C00085 -> C00354
COMPOUND    C00267  alpha-D-Glucose
            C00022  Pyruvate
ORTHOLOGY   K00844  hexokinase [EC:2.7.1.1]
///
"""


def test_kegg_get_module_parse():
    """Parse a KEGG MODULE record into definition, reactions, compounds, pathways."""
    tool = _kegg_tool("get_module")
    with patch(
        "tooluniverse.kegg_ext_tool.requests.get",
        return_value=_resp(200, text=_MODULE_TEXT),
    ):
        out = tool.run({"module_id": "M00001"})
    assert out["status"] == "success"
    data = out["data"]
    assert data["name"].startswith("Glycolysis")
    assert data["definition"].startswith("(K00844")
    assert "Carbohydrate metabolism" in data["class"]
    rids = [r["reaction_id"] for r in data["reactions"]]
    assert "R00299" in rids and "R00756" in rids
    cids = [c["compound_id"] for c in data["compounds"]]
    assert "C00267" in cids
    assert "map00010" in data["pathways"]


def test_kegg_get_module_missing_id():
    """Missing module_id returns an error."""
    tool = _kegg_tool("get_module")
    out = tool.run({})
    assert out["status"] == "error"
    assert "module_id" in out["error"]


def test_kegg_get_module_http_error_no_raise():
    """An HTTP error is caught and returned as status=error."""
    tool = _kegg_tool("get_module")
    bad = _resp(404, text="")
    bad.raise_for_status.side_effect = __import__("requests").exceptions.HTTPError(
        response=_resp(404)
    )
    with patch("tooluniverse.kegg_ext_tool.requests.get", return_value=bad):
        out = tool.run({"module_id": "M99999"})
    assert out["status"] == "error"


# --------------------------------------------------------------------------- #
# KEGG_get_reaction
# --------------------------------------------------------------------------- #
_REACTION_TEXT = """ENTRY       R00200                      Reaction
NAME        ATP:pyruvate 2-O-phosphotransferase
DEFINITION  ATP + Pyruvate <=> ADP + Phosphoenolpyruvate
EQUATION    C00002 + C00022 <=> C00008 + C00074
RCLASS      RC00002  C00002_C00008
            RC00015  C00022_C00074
ENZYME      2.7.1.40
PATHWAY     rn00010  Glycolysis / Gluconeogenesis
            rn00620  Pyruvate metabolism
MODULE      M00001  Glycolysis (Embden-Meyerhof pathway)
///
"""


def test_kegg_get_reaction_parse():
    """Parse a KEGG REACTION record: equation, enzyme, rclass, pathways, modules."""
    tool = _kegg_tool("get_reaction")
    with patch(
        "tooluniverse.kegg_ext_tool.requests.get",
        return_value=_resp(200, text=_REACTION_TEXT),
    ):
        out = tool.run({"reaction_id": "R00200"})
    assert out["status"] == "success"
    data = out["data"]
    assert data["name"] == "ATP:pyruvate 2-O-phosphotransferase"
    assert data["equation"] == "C00002 + C00022 <=> C00008 + C00074"
    assert data["enzymes"] == ["2.7.1.40"]
    assert any(rc.startswith("RC00002") for rc in data["rclass"])
    assert "rn00010" in data["pathways"]
    assert "M00001" in data["modules"]


def test_kegg_get_reaction_missing_id():
    """Missing reaction_id returns an error."""
    tool = _kegg_tool("get_reaction")
    out = tool.run({})
    assert out["status"] == "error"
    assert "reaction_id" in out["error"]


# --------------------------------------------------------------------------- #
# KEGG_get_enzyme
# --------------------------------------------------------------------------- #
_ENZYME_TEXT = """ENTRY       EC 2.7.1.1                  Enzyme
NAME        hexokinase;
            hexokinase type IV glucokinase;
            glucose ATP phosphotransferase
CLASS       Transferases;
            Transferring phosphorus-containing groups;
            Phosphotransferases with an alcohol group as acceptor
SYSNAME     ATP:D-hexose 6-phosphotransferase
REACTION    ATP + D-hexose = ADP + D-hexose 6-phosphate [RN:R02848]
SUBSTRATE   ATP [CPD:C00002];
            D-hexose [CPD:C00738]
PRODUCT     ADP [CPD:C00008];
            D-hexose 6-phosphate [CPD:C02965]
ORTHOLOGY   K00844  hexokinase [EC:2.7.1.1]
///
"""


def test_kegg_get_enzyme_parse():
    """Parse a KEGG ENZYME record: names, CLASS tree, sysname, reaction, orthologs."""
    tool = _kegg_tool("get_enzyme")
    with patch(
        "tooluniverse.kegg_ext_tool.requests.get",
        return_value=_resp(200, text=_ENZYME_TEXT),
    ):
        out = tool.run({"ec_number": "2.7.1.1"})
    assert out["status"] == "success"
    data = out["data"]
    assert "hexokinase" in data["names"]
    assert len(data["names"]) == 3
    assert data["class"][0] == "Transferases"
    assert len(data["class"]) == 3
    assert data["sysname"] == "ATP:D-hexose 6-phosphotransferase"
    assert "R02848" in data["reaction"]
    assert "K00844" in data["orthology"]


def test_kegg_get_enzyme_missing_id():
    """Missing ec_number returns an error."""
    tool = _kegg_tool("get_enzyme")
    out = tool.run({})
    assert out["status"] == "error"
    assert "ec_number" in out["error"]


# --------------------------------------------------------------------------- #
# WikiPathways_get_pathway_metabolites
# --------------------------------------------------------------------------- #
_WP_SPARQL_RESULT = {
    "results": {
        "bindings": [
            {
                "metabolite": {"value": "https://identifiers.org/hmdb/HMDB0000122"},
                "label": {"value": "GLU"},
                "identifier": {"value": "https://identifiers.org/hmdb/HMDB0000122"},
                "source": {"value": "HMDB"},
            },
            {
                "metabolite": {"value": "https://identifiers.org/hmdb/HMDB0000122"},
                "label": {"value": "D-Glucose"},
                "identifier": {"value": "https://identifiers.org/hmdb/HMDB0000122"},
                "source": {"value": "HMDB"},
            },
            {
                "metabolite": {"value": "https://identifiers.org/hmdb/HMDB0001112"},
                "label": {"value": "D-Glyceraldehyde 3-phosphate"},
                "identifier": {"value": "https://identifiers.org/hmdb/HMDB0001112"},
                "source": {"value": "HMDB"},
            },
        ]
    }
}


def _fake_urlopen(payload):
    class _Ctx:
        def __enter__(self_inner):
            return io.BytesIO(json.dumps(payload).encode("utf-8"))

        def __exit__(self_inner, *a):
            return False

    return lambda *a, **k: _Ctx()


def test_wikipathways_metabolites_parse():
    """Collapse SPARQL rows to distinct metabolites with descriptive labels."""
    tool = _wp_tool("get_pathway_metabolites")
    with patch(
        "tooluniverse.wikipathways_ext_tool.urlopen",
        _fake_urlopen(_WP_SPARQL_RESULT),
    ):
        out = tool.run({"pathway_id": "WP534"})
    assert out["status"] == "success"
    data = out["data"]
    assert data["metabolite_count"] == 2  # two distinct metabolite nodes
    glucose = [
        m for m in data["metabolites"] if "HMDB0000122" in m["identifier"]
    ][0]
    # Descriptive label preferred over the all-caps abbreviation "GLU".
    assert glucose["label"] == "D-Glucose"
    assert glucose["source"] == "HMDB"
    labels = {m["label"] for m in data["metabolites"]}
    assert "D-Glyceraldehyde 3-phosphate" in labels


def test_wikipathways_metabolites_missing_id():
    """Missing pathway_id returns an error."""
    tool = _wp_tool("get_pathway_metabolites")
    out = tool.run({})
    assert out["status"] == "error"
    assert "pathway_id" in out["error"]


def test_wikipathways_metabolites_network_error_no_raise():
    """A network error is caught and returned as status=error."""
    tool = _wp_tool("get_pathway_metabolites")

    def _boom(*a, **k):
        raise OSError("connection refused")

    with patch("tooluniverse.wikipathways_ext_tool.urlopen", _boom):
        out = tool.run({"pathway_id": "WP534"})
    assert out["status"] == "error"
