"""Unit tests for the sequence-genomics depth tools.

All HTTP is mocked -- these tests never hit a live API. They cover the parse
path and the error path for four tools that reuse existing tool classes:

- EnsemblPheno_get_by_term         (EnsemblPhenotypeTool, endpoint_type="term")
- Ensembl_get_transcript_haplotypes (EnsemblRESTTool, transcript_haplotypes)
- RNAcentral_get_xrefs_and_pubs    (RNAcentralGetTool, sub_resources)
- UCSC_list_tracks                 (UCSCGenomeTool, endpoint_type="list_tracks")
"""

import pytest
import requests
from unittest.mock import patch, MagicMock

from tooluniverse.ensembl_phenotype_tool import EnsemblPhenotypeTool
from tooluniverse.ensembl_tool import EnsemblRESTTool
from tooluniverse.rnacentral_tool import RNAcentralGetTool
from tooluniverse.ucsc_genome_tool import UCSCGenomeTool

pytestmark = pytest.mark.unit


def _mock_response(status_code=200, json_data=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {}
    resp.raise_for_status.return_value = None
    resp.headers = {"content-type": "application/json"}
    return resp


# ---------------------------------------------------------------------------
# 1. EnsemblPheno_get_by_term  (reverse phenotype lookup)
# ---------------------------------------------------------------------------
def _term_tool():
    return EnsemblPhenotypeTool(
        {
            "name": "EnsemblPheno_get_by_term",
            "type": "EnsemblPhenotypeTool",
            "fields": {"endpoint_type": "term"},
        }
    )


_TERM_PAYLOAD = [
    {
        "description": "Alzheimer disease",
        "attributes": {
            "associated_gene": "APP",
            "risk_allele": "A",
            "p_value": "4.00e-11",
            "external_reference": "PMID:30617256",
        },
        "mapped_to_accession": "EFO:0000249",
        "Variation": "rs7810606",
        "source": "NHGRI-EBI GWAS catalog",
        "location": "7:143411065-143411065",
    }
]


def test_term_parse_by_name():
    """Term name lookup parses associations with variant/gene/risk-allele."""
    tool = _term_tool()
    with patch("tooluniverse.ensembl_phenotype_tool.requests.get") as mget:
        mget.return_value = _mock_response(json_data=_TERM_PAYLOAD)
        out = tool.run({"term": "Alzheimer disease"})

    assert out["status"] == "success"
    data = out["data"]
    assert data["query_kind"] == "term"
    assert data["association_count"] == 1
    assoc = data["associations"][0]
    assert assoc["variant"] == "rs7810606"
    assert assoc["gene"] == "APP"
    assert assoc["risk_allele"] == "A"
    assert assoc["p_value"] == "4.00e-11"
    assert assoc["source"] == "NHGRI-EBI GWAS catalog"
    # endpoint should be the /term/ variant
    assert "phenotype/term/" in out["metadata"]["endpoint"]


def test_term_accession_autodetected_from_term_arg():
    """An ontology-looking value passed as 'term' is routed to /accession/."""
    tool = _term_tool()
    with patch("tooluniverse.ensembl_phenotype_tool.requests.get") as mget:
        mget.return_value = _mock_response(json_data=_TERM_PAYLOAD)
        out = tool.run({"term": "EFO:0000249"})

    assert out["status"] == "success"
    assert out["data"]["query_kind"] == "accession"
    assert "phenotype/accession/" in out["metadata"]["endpoint"]


def test_term_requires_a_query():
    """Missing term and accession returns a structured error."""
    tool = _term_tool()
    out = tool.run({})
    assert out["status"] == "error"
    assert "term" in out["error"] or "accession" in out["error"]


def test_term_http_error_does_not_raise():
    """HTTP 404 from the term endpoint returns error, never raises."""
    tool = _term_tool()
    err = requests.exceptions.HTTPError()
    err.response = MagicMock(status_code=404)
    with patch("tooluniverse.ensembl_phenotype_tool.requests.get") as mget:
        mget.return_value.raise_for_status.side_effect = err
        out = tool.run({"term": "Nonexistent disease"})
    assert out["status"] == "error"


# ---------------------------------------------------------------------------
# 2. Ensembl_get_transcript_haplotypes  (EnsemblRESTTool)
# ---------------------------------------------------------------------------
def _haplo_tool():
    return EnsemblRESTTool(
        {
            "name": "Ensembl_get_transcript_haplotypes",
            "type": "EnsemblRESTTool",
            "endpoint": "/transcript_haplotypes/{species}/{id}",
            "parameter": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "species": {"type": "string", "default": "human"},
                },
                "required": ["id"],
            },
        }
    )


_HAPLO_PAYLOAD = {
    "transcript_id": "ENST00000288602",
    "total_haplotype_count": 6018,
    "protein_haplotypes": [
        {
            "name": "ENST00000288602:REF",
            "count": 5963,
            "frequency": 0.99086,
            "has_indel": 0,
            "population_frequencies": {"1000GENOMES:phase_3:JPT": 0.913},
            "contributing_variants": [],
        }
    ],
    "cds_haplotypes": [{"name": "x"}],
    "total_population_counts": {"1000GENOMES:phase_3:AMR": 694},
}


def test_haplotypes_parse():
    """Transcript haplotypes parse with population frequencies and counts."""
    tool = _haplo_tool()
    with patch("tooluniverse.ensembl_tool.request_with_retry") as mreq:
        mreq.return_value = _mock_response(json_data=_HAPLO_PAYLOAD)
        out = tool.run({"id": "ENST00000288602", "species": "human"})

    assert out["status"] == "success"
    data = out["data"]
    assert data["transcript_id"] == "ENST00000288602"
    assert len(data["protein_haplotypes"]) == 1
    ph = data["protein_haplotypes"][0]
    assert ph["count"] == 5963
    assert ph["population_frequencies"]["1000GENOMES:phase_3:JPT"] == 0.913
    # URL built from the endpoint template + species/id path params
    assert "transcript_haplotypes/human/ENST00000288602" in out["url"]


def test_haplotypes_missing_required_id():
    """Missing required transcript id returns a structured error."""
    tool = _haplo_tool()
    out = tool.run({"species": "human"})
    assert out["status"] == "error"
    assert "id" in out["error"]


def test_haplotypes_http_error_does_not_raise():
    """HTTP 400 returns a structured error, never raises."""
    tool = _haplo_tool()
    err = requests.exceptions.HTTPError()
    err.response = MagicMock(status_code=400, text="bad")
    with patch("tooluniverse.ensembl_tool.request_with_retry") as mreq:
        resp = _mock_response()
        resp.raise_for_status.side_effect = err
        mreq.return_value = resp
        out = tool.run({"id": "BOGUS"})
    assert out["status"] == "error"


# ---------------------------------------------------------------------------
# 3. RNAcentral_get_xrefs_and_pubs  (RNAcentralGetTool, sub_resources)
# ---------------------------------------------------------------------------
def _rnacentral_tool():
    return RNAcentralGetTool(
        {
            "name": "RNAcentral_get_xrefs_and_pubs",
            "type": "RNAcentralGetTool",
            "fields": {"sub_resources": ["xrefs", "publications"]},
            "settings": {"base_url": "https://rnacentral.org/api/v1", "timeout": 30},
        }
    )


_XREFS_PAYLOAD = {
    "count": 8,
    "results": [
        {
            "database": "Rfam",
            "taxid": 7955,
            "accession": {"id": "CR381647.10:84955..85035:rfam"},
            "ncbi_gene_id": None,
        }
    ],
}
_PUBS_PAYLOAD = {
    "count": 8,
    "results": [
        {
            "title": "Computational identification of Drosophila microRNA genes",
            "authors": ["Lai EC"],
            "pubmed_id": "12844358",
            "doi": "10.1186/gb-2003-4-7-r42",
        }
    ],
}


def test_rnacentral_xrefs_and_pubs_parse():
    """xrefs and publications are fetched and merged into one response."""
    tool = _rnacentral_tool()

    def fake_get(url, headers=None, timeout=30):
        if "/xrefs" in url:
            return _XREFS_PAYLOAD
        if "/publications" in url:
            return _PUBS_PAYLOAD
        raise AssertionError("unexpected url " + url)

    with patch("tooluniverse.rnacentral_tool._http_get", side_effect=fake_get):
        out = tool.run({"accession": "URS000063A371"})

    assert out["status"] == "success"
    data = out["data"]
    assert data["xrefs"]["count"] == 8
    assert data["publications"]["count"] == 8
    xr = data["xrefs"]["results"][0]
    assert xr["database"] == "Rfam"
    assert xr["taxid"] == 7955
    assert xr["accession"]["id"] == "CR381647.10:84955..85035:rfam"
    pub = data["publications"]["results"][0]
    assert pub["pubmed_id"] == "12844358"
    assert pub["doi"] == "10.1186/gb-2003-4-7-r42"


def test_rnacentral_requires_accession():
    """Missing accession returns a structured error."""
    tool = _rnacentral_tool()
    out = tool.run({})
    assert out["status"] == "error"
    assert "accession" in out["error"]


def test_rnacentral_all_subresources_fail_is_error():
    """All sub-resource fetches failing yields a structured error."""
    tool = _rnacentral_tool()
    with patch(
        "tooluniverse.rnacentral_tool._http_get",
        side_effect=Exception("boom"),
    ):
        out = tool.run({"accession": "URS000063A371"})
    assert out["status"] == "error"
    assert "boom" in out["error"]


# ---------------------------------------------------------------------------
# 4. UCSC_list_tracks  (UCSCGenomeTool, endpoint_type="list_tracks")
# ---------------------------------------------------------------------------
def _ucsc_tool():
    return UCSCGenomeTool(
        {
            "name": "UCSC_list_tracks",
            "type": "UCSCGenomeTool",
            "fields": {"endpoint_type": "list_tracks"},
        }
    )


_TRACKS_PAYLOAD = {
    "hg38": {
        "dbSnp155": {
            "shortLabel": "All dbSNP(155)",
            "type": "bigDbSnp",
            "longLabel": "All Short Genetic Variants from dbSNP Release 155",
            "parent": "dbSnp155ViewVariants off",
        },
        "knownGene": {
            "shortLabel": "GENCODE V44",
            "type": "bigGenePred",
            "longLabel": "GENCODE genes",
            "parent": None,
        },
    }
}
_SCHEMA_PAYLOAD = {
    "genome": "hg38",
    "track": "knownGene",
    "type": "bigGenePred",
    "shortLabel": "GENCODE V44",
    "longLabel": "GENCODE genes",
    "columnTypes": [
        {
            "name": "chrom",
            "sqlType": "varchar(255)",
            "jsonType": "string",
            "description": "Reference sequence chromosome or scaffold",
        },
        {
            "name": "chromStart",
            "sqlType": "int unsigned",
            "jsonType": "number",
            "description": "Start position in chromosome",
        },
    ],
}


def test_ucsc_list_tracks_parse_and_filter():
    """Track listing parses and name_filter narrows the results."""
    tool = _ucsc_tool()
    with patch("tooluniverse.ucsc_genome_tool.requests.get") as mget:
        mget.return_value = _mock_response(json_data=_TRACKS_PAYLOAD)
        out = tool.run({"genome": "hg38", "name_filter": "dbSnp"})

    assert out["status"] == "success"
    data = out["data"]
    # name_filter should keep only the dbSnp155 track
    assert data["track_count"] == 1
    assert data["tracks"][0]["track"] == "dbSnp155"
    assert data["tracks"][0]["type"] == "bigDbSnp"
    assert out["metadata"]["endpoint"] == "list/tracks"


def test_ucsc_list_tracks_no_filter_returns_all():
    """Listing without a filter returns every leaf track."""
    tool = _ucsc_tool()
    with patch("tooluniverse.ucsc_genome_tool.requests.get") as mget:
        mget.return_value = _mock_response(json_data=_TRACKS_PAYLOAD)
        out = tool.run({"genome": "hg38"})
    assert out["status"] == "success"
    assert out["data"]["track_count"] == 2


def test_ucsc_schema_mode_parse():
    """Providing a track returns its column schema instead of the list."""
    tool = _ucsc_tool()
    with patch("tooluniverse.ucsc_genome_tool.requests.get") as mget:
        mget.return_value = _mock_response(json_data=_SCHEMA_PAYLOAD)
        out = tool.run({"genome": "hg38", "track": "knownGene"})

    assert out["status"] == "success"
    data = out["data"]
    assert data["track"] == "knownGene"
    assert data["column_count"] == 2
    assert data["columns"][0]["name"] == "chrom"
    assert out["metadata"]["endpoint"] == "list/schema"


def test_ucsc_list_tracks_requires_genome():
    """Missing genome returns a structured error."""
    tool = _ucsc_tool()
    out = tool.run({})
    assert out["status"] == "error"
    assert "genome" in out["error"]


def test_ucsc_list_tracks_http_error_does_not_raise():
    """HTTP 400 returns a structured error, never raises."""
    tool = _ucsc_tool()
    err = requests.exceptions.HTTPError()
    err.response = MagicMock(status_code=400)
    with patch("tooluniverse.ucsc_genome_tool.requests.get") as mget:
        resp = _mock_response()
        resp.raise_for_status.side_effect = err
        mget.return_value = resp
        out = tool.run({"genome": "hg38"})
    assert out["status"] == "error"
