"""Unit tests for discovery-round batch 2 (Tark, MARRVEL, CTIS). Network mocked."""

from unittest.mock import MagicMock, patch

import tooluniverse.tark_tool as tark_mod
from tooluniverse.tark_tool import TarkManeTranscriptsTool, TarkTranscriptTool, _versioned
from tooluniverse.marrvel_tool import MARRVELGeneTool, MARRVELOmimTool
from tooluniverse.ctis_tool import CTISSearchTrialsTool, CTISGetTrialTool


def _resp(status=200, json_body=None):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = json_body
    r.raise_for_status.return_value = None
    return r


def _cfg(name, typ):
    return {"name": name, "type": typ, "parameter": {"type": "object", "properties": {}}}


# --------------------------- Tark --------------------------- #
def test_versioned_join():
    assert _versioned("ENST1", 8) == "ENST1.8"
    assert _versioned("ENST1", None) == "ENST1"
    assert _versioned(None, 3) is None


def test_tark_mane_requires_an_identifier():
    out = TarkManeTranscriptsTool(_cfg("Tark_get_mane_transcripts", "TarkManeTranscriptsTool")).run({})
    assert out["status"] == "error"
    assert "gene" in out["error"]


def test_tark_mane_filters_by_gene():
    tark_mod._MANE_CACHE = None  # reset module cache
    manelist = [
        {"ens_gene_name": "BRCA2", "ens_stable_id": "ENST00000380152", "ens_stable_id_version": "8",
         "refseq_stable_id": "NM_000059", "refseq_stable_id_version": "4", "mane_type": "MANE SELECT"},
        {"ens_gene_name": "AGO3", "ens_stable_id": "ENST00000373191", "ens_stable_id_version": "9",
         "refseq_stable_id": "NM_024852", "refseq_stable_id_version": "4", "mane_type": "MANE SELECT"},
    ]
    with patch("tooluniverse.tark_tool.requests.get", return_value=_resp(200, manelist)):
        out = TarkManeTranscriptsTool(_cfg("Tark_get_mane_transcripts", "TarkManeTranscriptsTool")).run({"gene": "brca2"})
    assert out["status"] == "success"
    assert len(out["data"]) == 1
    assert out["data"][0]["ensembl_transcript"] == "ENST00000380152.8"
    assert out["data"][0]["refseq_transcript"] == "NM_000059.4"
    tark_mod._MANE_CACHE = None  # clean up


def test_tark_mane_filters_by_refseq_base_id():
    tark_mod._MANE_CACHE = None
    manelist = [{"ens_gene_name": "BRCA2", "ens_stable_id": "ENST00000380152", "ens_stable_id_version": "8",
                 "refseq_stable_id": "NM_000059", "refseq_stable_id_version": "4", "mane_type": "MANE SELECT"}]
    with patch("tooluniverse.tark_tool.requests.get", return_value=_resp(200, manelist)):
        out = TarkManeTranscriptsTool(_cfg("Tark_get_mane_transcripts", "TarkManeTranscriptsTool")).run({"refseq_id": "NM_000059.99"})
    assert len(out["data"]) == 1  # version ignored, base id matched
    tark_mod._MANE_CACHE = None


def test_tark_transcript_requires_stable_id():
    out = TarkTranscriptTool(_cfg("Tark_get_transcript", "TarkTranscriptTool")).run({})
    assert out["status"] == "error"


def test_tark_transcript_curates():
    body = {"results": [{"stable_id": "ENST00000380152", "stable_id_version": "8", "assembly": "GRCh38",
                         "biotype": "protein_coding", "loc_region": "13", "loc_start": "1", "loc_end": "2",
                         "transcript_release_set": [{"shortname": "110"}, {"shortname": "111"}]}]}
    with patch("tooluniverse.tark_tool.requests.get", return_value=_resp(200, body)):
        out = TarkTranscriptTool(_cfg("Tark_get_transcript", "TarkTranscriptTool")).run({"stable_id": "ENST00000380152.8"})
    assert out["status"] == "success"
    assert out["data"][0]["stable_id"] == "ENST00000380152.8"
    assert out["data"][0]["releases"] == ["110", "111"]


# --------------------------- MARRVEL --------------------------- #
def test_marrvel_gene_requires_symbol():
    out = MARRVELGeneTool(_cfg("MARRVEL_get_gene", "MARRVELGeneTool")).run({})
    assert out["status"] == "error"


def test_marrvel_gene_curates_xrefs():
    rec = {"symbol": "CFTR", "name": "CF transmembrane regulator", "entrezId": 1080,
           "uniprotKBId": "P13569", "chr": "7", "location": "7q31.2", "type": "protein-coding",
           "alias": ["ABCC7"], "xref": {"omimId": "602421", "hgncId": "1884", "ensemblId": "ENSG00000001626"}}
    with patch("tooluniverse.marrvel_tool.requests.get", return_value=_resp(200, rec)):
        out = MARRVELGeneTool(_cfg("MARRVEL_get_gene", "MARRVELGeneTool")).run({"symbol": "CFTR"})
    assert out["data"]["omim_id"] == "602421"
    assert out["data"]["ensembl_id"] == "ENSG00000001626"
    assert out["data"]["uniprot_id"] == "P13569"


def test_marrvel_omim_curates_phenotypes():
    body = {"phenotypes": [{"mimNumber": 602421, "phenotype": "Cystic fibrosis",
                            "phenotypeMimNumber": 219700, "phenotypeInheritance": "Autosomal recessive"}]}
    with patch("tooluniverse.marrvel_tool.requests.get", return_value=_resp(200, body)):
        out = MARRVELOmimTool(_cfg("MARRVEL_get_omim_phenotypes", "MARRVELOmimTool")).run({"symbol": "CFTR"})
    assert out["status"] == "success"
    assert out["data"][0]["inheritance"] == "Autosomal recessive"
    assert out["data"][0]["phenotype_mim_number"] == 219700


# --------------------------- CTIS --------------------------- #
def test_ctis_search_requires_query():
    out = CTISSearchTrialsTool(_cfg("CTIS_search_trials", "CTISSearchTrialsTool")).run({})
    assert out["status"] == "error"


def test_ctis_search_curates_and_paginates():
    body = {"pagination": {"totalRecords": 505, "currentPage": 1, "totalPages": 101},
            "data": [{"ctNumber": "2022-503001-38-01", "ctTitle": "A phase III study",
                      "ctStatus": 5, "trialPhase": "Phase III", "sponsor": "ACME",
                      "trialCountries": ["DE", "FR"], "totalNumberEnrolled": 300}]}
    with patch("tooluniverse.ctis_tool.requests.post", return_value=_resp(200, body)):
        out = CTISSearchTrialsTool(_cfg("CTIS_search_trials", "CTISSearchTrialsTool")).run({"query": "breast cancer", "limit": 5})
    assert out["status"] == "success"
    assert out["metadata"]["total_records"] == 505
    assert out["data"][0]["ct_number"] == "2022-503001-38-01"
    assert out["data"][0]["countries"] == ["DE", "FR"]


def test_ctis_get_requires_ct_number():
    out = CTISGetTrialTool(_cfg("CTIS_get_trial", "CTISGetTrialTool")).run({})
    assert out["status"] == "error"


def test_ctis_get_404_is_empty_success():
    with patch("tooluniverse.ctis_tool.requests.get", return_value=_resp(404, None)):
        out = CTISGetTrialTool(_cfg("CTIS_get_trial", "CTISGetTrialTool")).run({"ct_number": "0000-000000-00-00"})
    assert out["status"] == "success"
    assert out["data"] == {}


# --------------------------- ClassyFire --------------------------- #
from tooluniverse.classyfire_tool import ClassyFireTool  # noqa: E402


def test_classyfire_requires_inchikey():
    out = ClassyFireTool(_cfg("ClassyFire_classify_by_inchikey", "ClassyFireTool")).run({})
    assert out["status"] == "error"
    assert "inchikey" in out["error"]


def test_classyfire_curates_taxonomy():
    rec = {"inchikey": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N", "smiles": "CC(=O)Oc1ccccc1C(=O)O",
           "kingdom": {"name": "Organic compounds", "chemont_id": "CHEMONTID:0000000"},
           "superclass": {"name": "Benzenoids"}, "class": {"name": "Benzene and substituted derivatives"},
           "subclass": {"name": "Benzoic acids and derivatives"},
           "direct_parent": {"name": "Acylsalicylic acids"},
           "intermediate_nodes": [{"name": "Salicylic acid and derivatives"}],
           "molecular_framework": "Aromatic homomonocyclic compounds",
           "substituents": ["Benzoic acid", "Phenol ester"], "description": "Aspirin..."}
    with patch("tooluniverse.classyfire_tool.requests.get", return_value=_resp(200, rec)):
        out = ClassyFireTool(_cfg("ClassyFire_classify_by_inchikey", "ClassyFireTool")).run(
            {"inchikey": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"})
    assert out["status"] == "success"
    d = out["data"]
    assert d["classified"] is True
    assert d["superclass"] == "Benzenoids"
    assert d["direct_parent"] == "Acylsalicylic acids"
    assert d["intermediate_nodes"] == ["Salicylic acid and derivatives"]


def test_classyfire_404_is_unclassified_success():
    with patch("tooluniverse.classyfire_tool.requests.get", return_value=_resp(404, None)):
        out = ClassyFireTool(_cfg("ClassyFire_classify_by_inchikey", "ClassyFireTool")).run(
            {"inchikey": "AAAAAAAAAAAAAA-BBBBBBBBBB-C"})
    assert out["status"] == "success"
    assert out["data"]["classified"] is False
