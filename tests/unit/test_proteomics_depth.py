"""Unit tests for the proteomics-depth tools.

Covers four tools that add identification/quantification-level depth to the
proteomics cluster, each reusing an existing tool class:

  - PRIDE_get_projects_for_protein        (PRIDERESTTool)
  - PDC_get_quant_data_matrix             (PDCTool)
  - ProteomicsDB_get_peptides_for_protein (ProteomicsDBTool)
  - MassIVE_get_protein_identifications   (MassIVETool)

Tests are fully mocked (no network) and check both the parse path and the
error path. Real-data live verification is done separately via the CLI.
"""

from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

import tooluniverse.pdc_tool as pdc_mod
import tooluniverse.proteomicsdb_tool as pdb_mod
import tooluniverse.massive_tool as massive_mod
from tooluniverse.pride_tool import PRIDERESTTool
from tooluniverse.pdc_tool import PDCTool
from tooluniverse.proteomicsdb_tool import ProteomicsDBTool
from tooluniverse.massive_tool import MassIVETool


def _resp(status_code=200, json_data=None, text=""):
    """Build a fake requests.Response-like object."""
    r = MagicMock()
    r.status_code = status_code
    r.text = text
    r.headers = {"content-type": "application/json"}
    if json_data is None:
        r.json.side_effect = ValueError("no json")
    else:
        r.json.return_value = json_data
    r.raise_for_status = MagicMock()
    return r


# --------------------------------------------------------------------------
# PRIDE_get_projects_for_protein  (PRIDERESTTool)
# --------------------------------------------------------------------------


def _pride_tool():
    return PRIDERESTTool(
        {
            "name": "PRIDE_get_projects_for_protein",
            "type": "PRIDERESTTool",
            "fields": {
                "endpoint": "https://www.ebi.ac.uk/pride/ws/archive/v2/proteins/{accession}"
            },
            "parameter": {"type": "object", "properties": {}},
        }
    )


def test_pride_projects_parse(monkeypatch):
    """PRIDE reverse lookup parses proteinAccession and project list."""
    tool = _pride_tool()
    payload = {
        "proteinAccession": "P38398",
        "projects": ["PXD054178", "PXD041817", "PXD029496"],
    }
    monkeypatch.setattr(
        "tooluniverse.pride_tool.request_with_retry",
        lambda *a, **k: _resp(200, payload),
    )
    out = tool.run({"accession": "P38398"})
    assert out["status"] == "success"
    assert out["data"]["proteinAccession"] == "P38398"
    assert out["data"]["projects"] == ["PXD054178", "PXD041817", "PXD029496"]
    # endpoint template was substituted
    assert out["url"].endswith("/proteins/P38398")


def test_pride_projects_http_error(monkeypatch):
    """PRIDE reverse lookup returns an error envelope on HTTP failure."""
    tool = _pride_tool()
    monkeypatch.setattr(
        "tooluniverse.pride_tool.request_with_retry",
        lambda *a, **k: _resp(404, None, text="not found"),
    )
    out = tool.run({"accession": "BOGUS"})
    assert out["status"] == "error"
    assert "error" in out


def test_pride_projects_never_raises(monkeypatch):
    """PRIDE reverse lookup never raises, even on transport exceptions."""
    tool = _pride_tool()

    def boom(*a, **k):
        raise RuntimeError("network down")

    monkeypatch.setattr("tooluniverse.pride_tool.request_with_retry", boom)
    out = tool.run({"accession": "P38398"})
    assert out["status"] == "error"


# --------------------------------------------------------------------------
# PDC_get_quant_data_matrix  (PDCTool)
# --------------------------------------------------------------------------


def _pdc_tool():
    return PDCTool(
        {
            "name": "PDC_get_quant_data_matrix",
            "type": "PDCTool",
            "parameter": {"type": "object", "properties": {}},
        }
    )


def test_pdc_quant_matrix_parse(monkeypatch):
    """PDC quant matrix parses header/aliquots and truncates gene rows."""
    tool = _pdc_tool()
    matrix = [
        ["Gene/Aliquot", "uuid1:CPT0026410003", "uuid2:CPT0002370001"],
        ["A1BG", "-1.0967", "0.1012"],
        ["A2M", "0.5", "-0.3"],
        ["TP53", "1.2", "0.0"],
    ]
    fake = _resp(200, {"data": {"quantDataMatrix": matrix}})
    monkeypatch.setattr(pdc_mod.requests, "post", lambda *a, **k: fake)

    out = tool.run(
        {
            "operation": "get_quant_data_matrix",
            "pdc_study_id": "PDC000127",
            "data_type": "log2_ratio",
            "max_genes": 2,
        }
    )
    assert out["status"] == "success"
    data = out["data"]
    assert data["num_genes"] == 3
    assert data["num_aliquots"] == 2
    assert data["aliquots"] == ["uuid1:CPT0026410003", "uuid2:CPT0002370001"]
    # truncated to max_genes=2
    assert data["num_genes_returned"] == 2
    assert data["truncated"] is True
    assert data["matrix"][0][0] == "A1BG"


def test_pdc_quant_matrix_missing_id():
    """PDC quant matrix errors when pdc_study_id is absent."""
    tool = _pdc_tool()
    out = tool.run({"operation": "get_quant_data_matrix"})
    assert out["status"] == "error"
    assert "pdc_study_id" in out["error"]


def test_pdc_quant_matrix_graphql_error(monkeypatch):
    """PDC quant matrix surfaces GraphQL errors as an error envelope."""
    tool = _pdc_tool()
    fake = _resp(200, {"errors": [{"message": "bad study"}]})
    monkeypatch.setattr(pdc_mod.requests, "post", lambda *a, **k: fake)
    out = tool.run({"operation": "get_quant_data_matrix", "pdc_study_id": "PDCXXXXXX"})
    assert out["status"] == "error"


def test_pdc_quant_matrix_empty(monkeypatch):
    """PDC quant matrix errors when no matrix is returned."""
    tool = _pdc_tool()
    fake = _resp(200, {"data": {"quantDataMatrix": None}})
    monkeypatch.setattr(pdc_mod.requests, "post", lambda *a, **k: fake)
    out = tool.run({"operation": "get_quant_data_matrix", "pdc_study_id": "PDC000127"})
    assert out["status"] == "error"


# --------------------------------------------------------------------------
# ProteomicsDB_get_peptides_for_protein  (ProteomicsDBTool)
# --------------------------------------------------------------------------


def _pdb_tool():
    return ProteomicsDBTool(
        {
            "name": "ProteomicsDB_get_peptides_for_protein",
            "type": "ProteomicsDBTool",
            "parameter": {"type": "object", "properties": {}},
        }
    )


def test_proteomicsdb_peptides_parse(monkeypatch):
    """ProteomicsDB peptides parse and coerce q-values to floats."""
    tool = _pdb_tool()
    payload = {
        "d": {
            "results": [
                {
                    "PEPTIDE_SEQUENCE": "ACGADSYEMEEDGVR",
                    "PEPTIDE_MASS": "1601.6",
                    "ISUNIQUE": 1,
                    "ISUNIQUE_PROTEIN": 1,
                    "PEPTIDE_Q_VALUE": "1.54e-23",
                    "PROTEIN_Q_VALUE": "2.07e-07",
                    "PEPTIDE_SCORE": "120.5",
                    "SEARCH_ENGINE": 1,
                    "START_POSITION": 10,
                    "END_POSITION": 24,
                    "EXPERIMENT_ID": 3066,
                    "EXPERIMENT_NAME": "Some experiment",
                    "PROJECT_NAME": "Halim_SciSignal_2013",
                    "PROJECT_DESCRIPTION": "desc",
                    "PUBMEDID": "23612710",
                    "GENE_NAME": "EGFR",
                    "PROTEIN_NAME": "Epidermal growth factor receptor",
                    "ENTRY_NAME": "EGFR_HUMAN",
                }
            ]
        }
    }
    monkeypatch.setattr(pdb_mod.requests, "get", lambda *a, **k: _resp(200, payload))

    out = tool.run(
        {
            "operation": "get_peptides_for_protein",
            "uniprot_id": "P00533",
            "max_results": 5,
        }
    )
    assert out["status"] == "success"
    data = out["data"]
    assert data["gene_name"] == "EGFR"
    assert data["num_peptides"] == 1
    pep = data["peptides"][0]
    assert pep["peptide_sequence"] == "ACGADSYEMEEDGVR"
    assert pep["is_unique"] == 1
    # numeric strings coerced to floats
    assert isinstance(pep["peptide_q_value"], float)
    assert pep["peptide_q_value"] == pytest.approx(1.54e-23)
    assert pep["project_name"] == "Halim_SciSignal_2013"


def test_proteomicsdb_peptides_missing_id():
    """ProteomicsDB peptides error when uniprot_id is absent."""
    tool = _pdb_tool()
    out = tool.run({"operation": "get_peptides_for_protein"})
    assert out["status"] == "error"
    assert "uniprot_id" in out["error"]


def test_proteomicsdb_peptides_empty(monkeypatch):
    """ProteomicsDB peptides return an empty list cleanly."""
    tool = _pdb_tool()
    payload = {"d": {"results": []}}
    monkeypatch.setattr(pdb_mod.requests, "get", lambda *a, **k: _resp(200, payload))
    out = tool.run({"operation": "get_peptides_for_protein", "uniprot_id": "P99999"})
    assert out["status"] == "success"
    assert out["data"]["num_peptides"] == 0


def test_proteomicsdb_peptides_http_error(monkeypatch):
    """ProteomicsDB peptides return an error envelope on HTTP failure."""
    tool = _pdb_tool()
    monkeypatch.setattr(
        pdb_mod.requests, "get", lambda *a, **k: _resp(500, None, text="boom")
    )
    out = tool.run({"operation": "get_peptides_for_protein", "uniprot_id": "P00533"})
    assert out["status"] == "error"


# --------------------------------------------------------------------------
# MassIVE_get_protein_identifications  (MassIVETool)
# --------------------------------------------------------------------------


def _massive_tool():
    return MassIVETool(
        {
            "name": "MassIVE_get_protein_identifications",
            "type": "MassIVETool",
            "fields": {"operation": "get_protein_identifications"},
            "parameter": {"type": "object", "properties": {}},
        }
    )


def test_massive_proteins_parse(monkeypatch):
    """MassIVE per-dataset proteins parse and coerce counts to int."""
    tool = _massive_tool()
    payload = [
        {
            "proteinAccession": "A2MP_MOUSE",
            "countPSM": "87187",
            "countPeptides": "58",
            "countPeptidoforms": "82",
            "countDatasets": "5",
        },
        {
            "proteinAccession": "A2M_MOUSE",
            "countPSM": "146131",
            "countPeptides": "106",
            "countPeptidoforms": "234",
            "countDatasets": "4",
        },
    ]
    monkeypatch.setattr(
        massive_mod.requests, "get", lambda *a, **k: _resp(200, payload)
    )
    out = tool.run({"accession": "PXD000561"})
    assert out["status"] == "success"
    data = out["data"]
    assert data["result_type"] == "proteins"
    assert data["count"] == 2
    first = data["proteins"][0]
    assert first["proteinAccession"] == "A2MP_MOUSE"
    # count strings coerced to int
    assert first["countPSM"] == 87187
    assert first["countDatasets"] == 5


def test_massive_cross_dataset_parse(monkeypatch):
    """MassIVE cross-dataset lookup hits proteins endpoint with proteinAccession."""
    tool = _massive_tool()
    payload = [
        {
            "proteinAccession": "A2M_MOUSE",
            "countPSM": "146131",
            "countPeptides": "106",
            "countPeptidoforms": "234",
            "countDatasets": "4",
        }
    ]
    captured = {}

    def fake_get(url, params=None, timeout=None):
        captured["url"] = url
        captured["params"] = params
        return _resp(200, payload)

    monkeypatch.setattr(massive_mod.requests, "get", fake_get)
    out = tool.run({"protein_accession": "A2M_MOUSE"})
    assert out["status"] == "success"
    assert out["data"]["count"] == 1
    assert out["data"]["proteins"][0]["countDatasets"] == 4
    # cross-dataset lookup hits the proteins endpoint with proteinAccession
    assert captured["url"].endswith("/proteins")
    assert captured["params"]["proteinAccession"] == "A2M_MOUSE"


def test_massive_psms_parse(monkeypatch):
    """MassIVE PSM lookup parses peptide sequence and charge from /psms."""
    tool = _massive_tool()
    payload = [
        {"peptideSequence": "DAEDAMDAMDGAVLDGR", "charge": "2"},
        {"peptideSequence": "QINDYVEK", "charge": "1"},
    ]
    captured = {}

    def fake_get(url, params=None, timeout=None):
        captured["url"] = url
        return _resp(200, payload)

    monkeypatch.setattr(massive_mod.requests, "get", fake_get)
    out = tool.run({"accession": "PXD000561", "result_type": "psms"})
    assert out["status"] == "success"
    assert out["data"]["result_type"] == "psms"
    assert out["data"]["count"] == 2
    assert out["data"]["psms"][0]["peptideSequence"] == "DAEDAMDAMDGAVLDGR"
    assert out["data"]["psms"][0]["charge"] == 2
    assert captured["url"].endswith("/psms")


def test_massive_missing_args():
    """MassIVE identifications error when neither accession is given."""
    tool = _massive_tool()
    out = tool.run({})
    assert out["status"] == "error"
    assert "accession" in out["error"]


def test_massive_http_error(monkeypatch):
    """MassIVE identifications return an error envelope on connection failure."""
    tool = _massive_tool()

    def boom(*a, **k):
        import requests

        raise requests.exceptions.ConnectionError("down")

    monkeypatch.setattr(massive_mod.requests, "get", boom)
    out = tool.run({"accession": "PXD000561"})
    assert out["status"] == "error"


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-q"]))
