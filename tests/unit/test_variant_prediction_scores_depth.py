"""Unit tests for the variant-prediction-scores depth tools.

Covers four new ToolUniverse tools that close confirmed, keyless capability
gaps. Each tool is exercised with a mocked HTTP layer for both the success
(parse) path and an error path. No network access is performed.

Tools under test:
  - MaveDB_get_mapped_variants (MaveDBTool, operation=get_mapped_variants):
    flattens the score set's GA4GH VRS / ClinGen Allele ID mapped variants,
    surfacing genomic SequenceLocation (chromosome end) and the ClinGen allele id.
  - MaveDB_get_clinical_controls (MaveDBTool, operation=get_clinical_controls):
    returns overlapping ClinVar pathogenic/benign/VUS controls plus a
    significance breakdown and the linked MaveDB variant URNs.
  - MaveDB_get_gnomad_variants (MaveDBTool, operation=get_gnomad_variants):
    returns gnomAD allele count/number/frequency variants observed in the set
    with their mapped genomic VRS alleles.
  - GenomeNexus_annotate_dbsnp (GenomeNexusTool, endpoint=annotate_dbsnp):
    annotates a dbSNP rsID and projects VEP + SIFT + PolyPhen + AlphaMissense
    transcript consequences via the shared _format_annotation path.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.mavedb_tool import MaveDBTool
from tooluniverse.genome_nexus_tool import GenomeNexusTool

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _fake_response(status_code=200, json_body=None, text=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.headers = {"content-type": "application/json"}
    resp.text = text if text is not None else json.dumps(json_body or {})
    if json_body is None and text is None:
        resp.json.side_effect = ValueError("no json")
    else:
        resp.json.return_value = json_body
    resp.raise_for_status.return_value = None
    return resp


def _mavedb_tool(operation):
    return MaveDBTool({"name": f"test_{operation}", "fields": {"operation": operation}})


def _genome_nexus_tool(endpoint):
    return GenomeNexusTool({"name": f"test_{endpoint}", "fields": {"endpoint": endpoint}})


# --------------------------------------------------------------------------- #
# MaveDB_get_mapped_variants
# --------------------------------------------------------------------------- #
_MAPPED_BODY = [
    {
        # intronic / unmappable: post_mapped is null, error_message set
        "preMapped": None,
        "postMapped": None,
        "vrsVersion": "2",
        "errorMessage": "ValueError: Variant is intronic and cannot be processed",
        "current": True,
        "alignmentLevel": "genomic",
        "variantUrn": "urn:mavedb:00001263-a-2#1",
        "clingenAlleleId": None,
        "recordType": "MappedVariant",
    },
    {
        # fully mapped: genomic SequenceLocation + ClinGen allele id
        "preMapped": {
            "id": "ga4gh:VA.pre",
            "state": {"type": "LiteralSequenceExpression", "sequence": "C"},
            "location": {
                "start": 266,
                "end": 267,
                "sequenceReference": {"label": "NM_000059.4", "refgetAccession": "SQ.x"},
            },
        },
        "postMapped": {
            "id": "ga4gh:VA.hecrf0q5PEydes_VYydUCM-pEXIyS_wo",
            "state": {"type": "LiteralSequenceExpression", "sequence": "C"},
            "location": {
                "start": 32319076,
                "end": 32319077,
                "sequenceReference": {
                    "label": "NC_000013.11",
                    "refgetAccession": "SQ._0wi-qoDrvram155UmcSC-zA5ZK4fpLT",
                },
            },
            "expressions": [{"value": "NC_000013.11:g.32319077A>C", "syntax": "hgvs.g"}],
        },
        "vrsVersion": "2",
        "errorMessage": None,
        "current": True,
        "alignmentLevel": "genomic",
        "variantUrn": "urn:mavedb:00001263-a-2#40",
        "clingenAlleleId": "CA387754009",
        "recordType": "MappedVariant",
    },
]


def test_mapped_variants_parse():
    """Parse mapped variants: genomic VRS location + ClinGen allele id, intronic null."""
    tool = _mavedb_tool("get_mapped_variants")
    with patch.object(tool.session, "get", return_value=_fake_response(json_body=_MAPPED_BODY)):
        out = tool.run({"urn": "urn:mavedb:00001263-a-2"})

    assert out["status"] == "success"
    data = out["data"]
    assert data["total_mapped_variants"] == 2
    assert data["n_with_genomic_location"] == 1
    assert data["n_with_clingen_allele_id"] == 1

    mapped = {mv["variant_urn"]: mv for mv in data["mapped_variants"]}
    intronic = mapped["urn:mavedb:00001263-a-2#1"]
    assert intronic["post_mapped"] is None
    assert intronic["clingen_allele_id"] is None
    assert "intronic" in intronic["error_message"]

    full = mapped["urn:mavedb:00001263-a-2#40"]
    assert full["clingen_allele_id"] == "CA387754009"
    assert full["post_mapped"]["end"] == 32319077
    assert full["post_mapped"]["sequence_reference_label"] == "NC_000013.11"
    assert full["post_mapped"]["hgvs_expressions"] == ["NC_000013.11:g.32319077A>C"]


def test_mapped_variants_limit_truncates():
    """limit truncates returned list while counts reflect the full set."""
    tool = _mavedb_tool("get_mapped_variants")
    with patch.object(tool.session, "get", return_value=_fake_response(json_body=_MAPPED_BODY)):
        out = tool.run({"urn": "urn:mavedb:00001263-a-2", "limit": 1})
    assert out["status"] == "success"
    # counts reflect the full set; returned/truncated reflect the cap
    assert out["data"]["total_mapped_variants"] == 2
    assert out["data"]["returned"] == 1
    assert out["data"]["truncated"] is True


def test_mapped_variants_missing_urn():
    """Missing urn returns a structured error, never raises."""
    tool = _mavedb_tool("get_mapped_variants")
    out = tool.run({})
    assert out["status"] == "error"
    assert "urn" in out["error"].lower()


def test_mapped_variants_http_error():
    """HTTP 404 from MaveDB maps to a not-found error."""
    tool = _mavedb_tool("get_mapped_variants")
    with patch.object(tool.session, "get", return_value=_fake_response(status_code=404)):
        out = tool.run({"urn": "urn:mavedb:99999999-z-9"})
    assert out["status"] == "error"
    assert "not found" in out["error"].lower()


# --------------------------------------------------------------------------- #
# MaveDB_get_clinical_controls
# --------------------------------------------------------------------------- #
_CONTROLS_BODY = [
    {
        "dbIdentifier": "617915",
        "geneSymbol": "BRCA2",
        "clinicalSignificance": "Uncertain significance",
        "clinicalReviewStatus": "criteria provided, multiple submitters, no conflicts",
        "dbVersion": "01_2025",
        "dbName": "ClinVar",
        "recordType": "ClinicalControlWithMappedVariants",
        "mappedVariants": [{"variantUrn": "urn:mavedb:00001263-a-2#41"}],
    },
    {
        "dbIdentifier": "51061",
        "geneSymbol": "BRCA2",
        "clinicalSignificance": "Pathogenic",
        "clinicalReviewStatus": "reviewed by expert panel",
        "dbVersion": "01_2025",
        "dbName": "ClinVar",
        "recordType": "ClinicalControlWithMappedVariants",
        "mappedVariants": [{"variantUrn": "urn:mavedb:00001263-a-2#99"}],
    },
]


def test_clinical_controls_parse():
    """Parse ClinVar clinical controls with significance breakdown and mapped URNs."""
    tool = _mavedb_tool("get_clinical_controls")
    with patch.object(tool.session, "get", return_value=_fake_response(json_body=_CONTROLS_BODY)):
        out = tool.run({"urn": "urn:mavedb:00001263-a-2"})

    assert out["status"] == "success"
    data = out["data"]
    assert data["total_clinical_controls"] == 2
    assert data["significance_breakdown"]["Pathogenic"] == 1
    assert data["significance_breakdown"]["Uncertain significance"] == 1
    first = data["clinical_controls"][0]
    assert first["db_identifier"] == "617915"
    assert first["gene_symbol"] == "BRCA2"
    assert first["mapped_variant_urns"] == ["urn:mavedb:00001263-a-2#41"]


def test_clinical_controls_significance_filter():
    """clinical_significance filter keeps only matching controls."""
    tool = _mavedb_tool("get_clinical_controls")
    with patch.object(tool.session, "get", return_value=_fake_response(json_body=_CONTROLS_BODY)):
        out = tool.run(
            {"urn": "urn:mavedb:00001263-a-2", "clinical_significance": "pathogenic"}
        )
    assert out["status"] == "success"
    assert out["data"]["total_clinical_controls"] == 1
    assert out["data"]["clinical_controls"][0]["clinical_significance"] == "Pathogenic"


def test_clinical_controls_http_error():
    """HTTP 500 from MaveDB surfaces as a structured error."""
    tool = _mavedb_tool("get_clinical_controls")
    with patch.object(tool.session, "get", return_value=_fake_response(status_code=500)):
        out = tool.run({"urn": "urn:mavedb:00001263-a-2"})
    assert out["status"] == "error"
    assert "500" in out["error"]


# --------------------------------------------------------------------------- #
# MaveDB_get_gnomad_variants
# --------------------------------------------------------------------------- #
_GNOMAD_BODY = [
    {
        "dbName": "gnomAD",
        "dbIdentifier": "13-32319097-A-C",
        "dbVersion": "v4.1",
        "alleleCount": 1,
        "alleleNumber": 1611418,
        "alleleFrequency": 6.2e-07,
        "recordType": "GnomADVariantWithMappedVariants",
        "mappedVariants": [
            {
                "postMapped": {
                    "id": "ga4gh:VA.obuhRhFYbyKlnjH2ZI4ZsdyUy7tJZmjP",
                    "state": {"type": "LiteralSequenceExpression", "sequence": "C"},
                    "location": {
                        "start": 32319096,
                        "end": 32319097,
                        "sequenceReference": {
                            "label": "NC_000013.11",
                            "refgetAccession": "SQ._0wi",
                        },
                    },
                }
            }
        ],
    }
]


def test_gnomad_variants_parse():
    """Parse gnomAD AC/AN/AF variants with mapped genomic VRS alleles."""
    tool = _mavedb_tool("get_gnomad_variants")
    with patch.object(tool.session, "get", return_value=_fake_response(json_body=_GNOMAD_BODY)):
        out = tool.run({"urn": "urn:mavedb:00001263-a-2"})

    assert out["status"] == "success"
    data = out["data"]
    assert data["total_gnomad_variants"] == 1
    v = data["gnomad_variants"][0]
    assert v["db_identifier"] == "13-32319097-A-C"
    assert v["db_version"] == "v4.1"
    assert v["allele_count"] == 1
    assert v["allele_number"] == 1611418
    assert v["allele_frequency"] == pytest.approx(6.2e-07)
    assert v["mapped_genomic_alleles"][0]["end"] == 32319097
    assert v["mapped_genomic_alleles"][0]["sequence_reference_label"] == "NC_000013.11"


def test_gnomad_variants_empty():
    """Empty gnomAD list yields a success envelope with zero variants."""
    tool = _mavedb_tool("get_gnomad_variants")
    with patch.object(tool.session, "get", return_value=_fake_response(json_body=[])):
        out = tool.run({"urn": "urn:mavedb:00001263-a-2"})
    assert out["status"] == "success"
    assert out["data"]["total_gnomad_variants"] == 0
    assert out["data"]["gnomad_variants"] == []


def test_gnomad_variants_http_error():
    """HTTP 404 from gnomAD endpoint maps to a not-found error."""
    tool = _mavedb_tool("get_gnomad_variants")
    with patch.object(tool.session, "get", return_value=_fake_response(status_code=404)):
        out = tool.run({"urn": "urn:mavedb:bad"})
    assert out["status"] == "error"
    assert "not found" in out["error"].lower()


# --------------------------------------------------------------------------- #
# GenomeNexus_annotate_dbsnp
# --------------------------------------------------------------------------- #
_DBSNP_BODY = {
    "variant": "rs121913529",
    "id": "rs121913529",
    "assembly_name": "GRCh37",
    "most_severe_consequence": "missense_variant",
    "successfully_annotated": True,
    "transcript_consequences": [
        {
            "gene_symbol": "KRAS",
            "transcript_id": "ENST00000256078",
            "consequence_terms": ["missense_variant"],
            "hgvsp": "ENSP00000256078.4:p.Gly12Asp",
            "hgvsc": "ENST00000256078.4:c.35G>A",
            "amino_acids": "G/D",
            "polyphen_prediction": "probably_damaging",
            "polyphen_score": 0.999,
            "sift_prediction": "deleterious",
            "sift_score": 0.0,
            "alphaMissense": {"score": 0.9949, "pathogenicity": "pathogenic"},
            "canonical": 1,
        }
    ],
    "annotation_summary": {
        "genomicLocation": {
            "chromosome": "12",
            "start": 25398284,
            "end": 25398284,
        },
        "transcriptConsequences": [{"hugoGeneSymbol": "KRAS"}],
    },
    "hotspots": {"annotation": []},
    "colocatedVariants": [{"dbSnpId": "rs121913529"}],
}


def test_annotate_dbsnp_parse():
    """Parse dbSNP annotation: VEP + SIFT + PolyPhen + AlphaMissense + genomic location."""
    tool = _genome_nexus_tool("annotate_dbsnp")
    with patch("tooluniverse.genome_nexus_tool.requests.get", return_value=_fake_response(json_body=_DBSNP_BODY)):
        out = tool.run({"rsid": "rs121913529"})

    assert out["status"] == "success"
    data = out["data"]
    assert data["variant"] == "rs121913529"
    assert data["most_severe_consequence"] == "missense_variant"
    assert len(data["transcript_consequences"]) == 1
    tc = data["transcript_consequences"][0]
    assert tc["gene_symbol"] == "KRAS"
    assert tc["sift_prediction"] == "deleterious"
    assert tc["polyphen_prediction"] == "probably_damaging"
    assert tc["alphaMissense"]["score"] == pytest.approx(0.9949)
    assert tc["alphaMissense"]["pathogenicity"] == "pathogenic"
    assert data["annotation_summary"]["genomicLocation"]["chromosome"] == "12"
    assert data["annotation_summary"]["genomicLocation"]["start"] == 25398284


def test_annotate_dbsnp_list_response():
    """A list-wrapped single annotation is unwrapped and parsed."""
    # Some Genome Nexus endpoints wrap a single annotation in a list.
    tool = _genome_nexus_tool("annotate_dbsnp")
    with patch("tooluniverse.genome_nexus_tool.requests.get", return_value=_fake_response(json_body=[_DBSNP_BODY])):
        out = tool.run({"rsid": "rs121913529"})
    assert out["status"] == "success"
    assert out["data"]["variant"] == "rs121913529"


def test_annotate_dbsnp_bare_numeric_id():
    """A bare numeric id is prefixed with 'rs' in the request URL."""
    # A bare numeric id should be prefixed with 'rs' and still work.
    tool = _genome_nexus_tool("annotate_dbsnp")
    with patch("tooluniverse.genome_nexus_tool.requests.get", return_value=_fake_response(json_body=_DBSNP_BODY)) as mock_get:
        out = tool.run({"rsid": "121913529"})
    assert out["status"] == "success"
    called_url = mock_get.call_args[0][0]
    assert called_url.endswith("/annotation/dbsnp/rs121913529")


def test_annotate_dbsnp_missing_rsid():
    """Missing rsid returns a structured error, never raises."""
    tool = _genome_nexus_tool("annotate_dbsnp")
    out = tool.run({})
    assert out["status"] == "error"
    assert "rsid" in out["error"].lower()


def test_annotate_dbsnp_not_annotated():
    """successfully_annotated=False maps to a structured error."""
    tool = _genome_nexus_tool("annotate_dbsnp")
    body = {"variant": "rs999", "successfully_annotated": False, "errorMessage": "not found"}
    with patch("tooluniverse.genome_nexus_tool.requests.get", return_value=_fake_response(json_body=body)):
        out = tool.run({"rsid": "rs999"})
    assert out["status"] == "error"
    assert "not found" in out["error"].lower()


def test_annotate_dbsnp_http_error_does_not_raise():
    """An HTTPError from requests is caught and returned as an error envelope."""
    import requests

    tool = _genome_nexus_tool("annotate_dbsnp")
    err = requests.exceptions.HTTPError()
    err.response = MagicMock(status_code=404)
    bad = MagicMock()
    bad.raise_for_status.side_effect = err
    with patch("tooluniverse.genome_nexus_tool.requests.get", return_value=bad):
        out = tool.run({"rsid": "rs0000"})
    assert out["status"] == "error"
