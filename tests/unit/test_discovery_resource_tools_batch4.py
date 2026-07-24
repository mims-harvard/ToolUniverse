"""Unit tests for discovery-round batch 4 (NPAtlas, ISRCTN). Network mocked."""

from unittest.mock import MagicMock, patch

from tooluniverse.npatlas_tool import NPAtlasSearchTool, NPAtlasCompoundTool
from tooluniverse.isrctn_tool import ISRCTNSearchTool, ISRCTNGetTrialTool


def _resp(status=200, json_body=None, text=None):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = json_body
    r.text = text
    r.raise_for_status.return_value = None
    return r


def _cfg(name, typ):
    return {"name": name, "type": typ, "parameter": {"type": "object", "properties": {}}}


# --------------------------- NPAtlas --------------------------- #
def test_npatlas_search_requires_a_field():
    out = NPAtlasSearchTool(_cfg("NPAtlas_search_compounds", "NPAtlasSearchTool")).run({})
    assert out["status"] == "error"


def test_npatlas_search_curates():
    body = [{"npaid": "NPA019568", "original_name": "Penicillinolide A",
             "mol_formula": "C20H30O5", "mol_weight": "350.4", "inchikey": "ABC-DEF-G",
             "smiles": "CC", "origin_organism": {"genus": "Penicillium", "species": "sp."}}]
    with patch("tooluniverse.npatlas_tool.requests.post", return_value=_resp(200, body)):
        out = NPAtlasSearchTool(_cfg("NPAtlas_search_compounds", "NPAtlasSearchTool")).run({"name": "penicillin"})
    assert out["status"] == "success"
    assert out["data"][0]["npaid"] == "NPA019568"
    assert out["data"][0]["molecular_formula"] == "C20H30O5"


def test_npatlas_get_requires_npaid():
    out = NPAtlasCompoundTool(_cfg("NPAtlas_get_compound", "NPAtlasCompoundTool")).run({})
    assert out["status"] == "error"


def test_npatlas_get_curates_with_reference():
    body = {"npaid": "NPA000001", "original_name": "Curvularide C", "mol_formula": "C19H37NO5",
            "inchikey": "BZL", "smiles": "CC", "inchi": "InChI=1S",
            "origin_organism": {"taxon": "Curvularia sp."},
            "origin_reference": {"title": "Paper", "doi": "10.x", "journal": "J", "year": 2011}}
    with patch("tooluniverse.npatlas_tool.requests.get", return_value=_resp(200, body)):
        out = NPAtlasCompoundTool(_cfg("NPAtlas_get_compound", "NPAtlasCompoundTool")).run({"npaid": "NPA000001"})
    assert out["data"]["origin_organism"] == "Curvularia sp."
    assert out["data"]["origin_reference"]["doi"] == "10.x"


def test_npatlas_get_404_empty():
    with patch("tooluniverse.npatlas_tool.requests.get", return_value=_resp(404)):
        out = NPAtlasCompoundTool(_cfg("NPAtlas_get_compound", "NPAtlasCompoundTool")).run({"npaid": "NPA999999"})
    assert out["status"] == "success"
    assert out["data"] == {}


# --------------------------- ISRCTN --------------------------- #
_XML = """<allTrials totalCount="42" xmlns="http://www.67bricks.com/isrctn">
  <fullTrial><trial>
    <isrctn>12336055</isrctn>
    <trialDescription>
      <title>A CGM study</title>
      <scientificTitle>Single arm CGM study</scientificTitle>
      <acronym>INITIATE-CGM</acronym>
    </trialDescription>
    <externalRefs><doi>10.1186/ISRCTN12336055</doi><eudraCTNumber>2026-526711-10-00</eudraCTNumber></externalRefs>
    <trialDesign><primaryStudyDesign>Interventional</primaryStudyDesign><overallEndDate>2027-06-01T00:00:00.000Z</overallEndDate></trialDesign>
  </trial></fullTrial>
</allTrials>"""


def test_isrctn_search_requires_query():
    out = ISRCTNSearchTool(_cfg("ISRCTN_search_trials", "ISRCTNSearchTool")).run({})
    assert out["status"] == "error"


def test_isrctn_search_parses_xml():
    with patch("tooluniverse.isrctn_tool.requests.get", return_value=_resp(200, text=_XML)):
        out = ISRCTNSearchTool(_cfg("ISRCTN_search_trials", "ISRCTNSearchTool")).run({"query": "cgm", "limit": 5})
    assert out["status"] == "success"
    assert out["metadata"]["total_available"] == "42"
    t = out["data"][0]
    assert t["isrctn_id"] == "ISRCTN12336055"
    assert t["title"] == "A CGM study"
    assert t["acronym"] == "INITIATE-CGM"
    assert t["eudract_number"] == "2026-526711-10-00"
    assert t["primary_study_design"] == "Interventional"


def test_isrctn_get_strips_prefix_and_parses():
    with patch("tooluniverse.isrctn_tool.requests.get", return_value=_resp(200, text=_XML)):
        out = ISRCTNGetTrialTool(_cfg("ISRCTN_get_trial", "ISRCTNGetTrialTool")).run({"isrctn_id": "ISRCTN12336055"})
    assert out["status"] == "success"
    assert out["data"]["isrctn_id"] == "ISRCTN12336055"
    assert out["metadata"]["query_isrctn_id"] == "ISRCTN12336055"


def test_isrctn_get_not_found():
    empty = '<allTrials totalCount="0" xmlns="http://www.67bricks.com/isrctn"></allTrials>'
    with patch("tooluniverse.isrctn_tool.requests.get", return_value=_resp(200, text=empty)):
        out = ISRCTNGetTrialTool(_cfg("ISRCTN_get_trial", "ISRCTNGetTrialTool")).run({"isrctn_id": "99999999"})
    assert out["status"] == "success"
    assert out["data"] == {}
