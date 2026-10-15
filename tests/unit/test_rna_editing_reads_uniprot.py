"""RNA editing comes from UniProt, because the Proteins API serves none.

EBI still documents /rna-editing in its own openapi.json, in both the
path and query forms, so the tool was calling it correctly. The dataset behind
it is empty: ?offset=0&size=1&taxid=<tx> returns 0 records for human, mouse,
rat and fly alike, and /rna-editing/P42262 answers 404 "Can not find Features
for accession" for GRIA2 -- the textbook Q/R editing site. Those two 404s were
the failures the weekly health check reported for ebi_proteins_ext.

UniProtKB curates the annotation, so the tool reads cc_rna_editing from there.
These tests stub the HTTP layer; the live shapes they encode were taken from
real responses for P42262 and P28335.
"""

import pytest

from tooluniverse.ebi_proteins_ext_tool import EBIProteinsExtTool

pytestmark = pytest.mark.unit

CONFIG = {
    "name": "EBIProteins_get_rna_editing",
    "type": "EBIProteinsExtTool",
    "fields": {"endpoint": "rna_editing"},
    "parameter": {
        "type": "object",
        "properties": {"accession": {"type": "string"}},
        "required": ["accession"],
    },
}

# 5HT2C as UniProt returns it: three edited positions, one shared citation.
_P28335 = {
    "primaryAccession": "P28335",
    "uniProtkbId": "5HT2C_HUMAN",
    "comments": [
        {
            "commentType": "RNA EDITING",
            "locationType": "Known",
            "positions": [
                {
                    "position": str(p),
                    "evidences": [
                        {
                            "evidenceCode": "ECO:0000269",
                            "source": "PubMed",
                            "id": "9928237",
                        }
                    ],
                }
                for p in (156, 158, 160)
            ],
            "note": {"texts": [{"value": "Partially edited."}]},
        }
    ],
}


class _Response:
    def __init__(self, status, payload=None):
        self.status_code = status
        self._payload = payload

    def json(self):
        if self._payload is None:
            raise ValueError("not json")
        return self._payload


def _run(monkeypatch, response, accession="P28335", capture=None):
    tool = EBIProteinsExtTool(CONFIG)

    def fake_get(url, params=None, **kwargs):
        if capture is not None:
            capture.update(url=url, params=params)
        return response

    monkeypatch.setattr("tooluniverse.ebi_proteins_ext_tool.requests.get", fake_get)
    return tool.run({"accession": accession})


def test_it_queries_uniprot_and_not_the_empty_ebi_endpoint(monkeypatch):
    seen = {}
    result = _run(monkeypatch, _Response(200, _P28335), capture=seen)

    assert "rest.uniprot.org" in seen["url"], (
        "the Proteins API /rna-editing dataset is empty for every taxon; "
        f"requested {seen['url']}"
    )
    assert "proteins/api" not in seen["url"]
    assert seen["params"]["fields"] == "cc_rna_editing,accession,id"
    assert result["status"] == "success"


def test_every_curated_position_and_its_evidence_survives(monkeypatch):
    data = _run(monkeypatch, _Response(200, _P28335))["data"]

    assert [s["position"] for s in data["rna_editing_sites"]] == [156, 158, 160], (
        "positions must come through as numbers, not UniProt's strings"
    )
    assert data["total_sites"] == 3
    assert data["entry_name"] == "5HT2C_HUMAN"
    assert data["location_type"] == "Known"
    assert data["rna_editing_sites"][0]["evidences"] == [
        {"code": "ECO:0000269", "source": "PubMed", "id": "9928237"}
    ], "the PubMed citation is the only provenance for an edited site"
    assert data["notes"][0]["text"] == "Partially edited."


def test_an_entry_with_no_editing_is_a_success_not_an_error(monkeypatch):
    """TP53 is not RNA-edited. That is an answer about TP53."""
    result = _run(
        monkeypatch,
        _Response(200, {"primaryAccession": "P04637", "uniProtkbId": "P53_HUMAN"}),
        accession="P04637",
    )

    assert result["status"] == "success"
    assert result["data"]["rna_editing_sites"] == []
    assert result["data"]["total_sites"] == 0
    assert result["data"]["location_type"] is None, (
        "absent is not the same as UniProt saying the location is undetermined"
    )


@pytest.mark.parametrize("status", [400, 404])
def test_an_unknown_accession_is_reported_the_same_either_way(monkeypatch, status):
    """UniProt answers 404 for one it lacks and 400 for one it cannot parse."""
    result = _run(monkeypatch, _Response(status), accession="NOTANACC")

    assert result["status"] == "error"
    assert "NOTANACC" in result["error"]
    assert "P42262" in result["error"], "say what a valid accession looks like"


def test_the_metadata_names_uniprot_as_the_source(monkeypatch):
    """A caller comparing results over time must see the source changed."""
    meta = _run(monkeypatch, _Response(200, _P28335))["metadata"]

    assert "UniProt" in meta["source"]
    assert "serves no records" in meta["source_note"]


def test_an_upstream_failure_is_not_reported_as_no_editing(monkeypatch):
    result = _run(monkeypatch, _Response(500))

    assert result["status"] == "error"
    assert "500" in result["error"]
