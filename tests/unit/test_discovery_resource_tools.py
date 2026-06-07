"""Unit tests for discovery-round resource tools (OPSIN, FAVOR, NCBI genome).

Network is mocked so these run in CI. They cover the deterministic logic the live
APIs cannot exercise repeatably:
  - FAVOR variant-string normalization + 404/empty handling
  - OPSIN success / unparseable-name / input-validation handling
  - NCBI Datasets genome assembly curation + dispatch
"""

from unittest.mock import MagicMock, patch

import requests

from tooluniverse.favor_tool import FAVORVariantAnnotationTool, _normalize_variant
from tooluniverse.opsin_tool import OPSINNameToStructureTool
from tooluniverse.ncbi_datasets_tool import NCBIDatasetsTool


def _resp(status=200, json_body=None):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = json_body
    r.raise_for_status.return_value = None
    return r


# --------------------------------------------------------------------------- #
# FAVOR
# --------------------------------------------------------------------------- #
def _favor():
    return FAVORVariantAnnotationTool(
        {"name": "FAVOR_annotate_variant", "type": "FAVORVariantAnnotationTool",
         "parameter": {"type": "object", "properties": {}}}
    )


def test_normalize_variant_accepts_multiple_formats():
    assert _normalize_variant("19-44908822-C-T") == "19-44908822-C-T"
    assert _normalize_variant("chr19:44908822:C:T") == "19-44908822-C-T"
    assert _normalize_variant("CHR19_44908822_c_t") == "19-44908822-C-T"


def test_normalize_variant_rejects_malformed():
    assert _normalize_variant("rs7412") is None
    assert _normalize_variant("19-44908822-C") is None
    assert _normalize_variant("19-notapos-C-T") is None
    assert _normalize_variant("") is None


def test_favor_bad_variant_returns_error():
    out = _favor().run({"variant": "rs7412"})
    assert out["status"] == "error"
    assert "chr-pos-ref-alt" in out["error"]


def test_favor_404_is_success_not_found():
    with patch("tooluniverse.favor_tool.requests.get", return_value=_resp(404)):
        out = _favor().run({"variant": "19-1-C-T"})
    assert out["status"] == "success"
    assert out["data"]["found"] is False
    assert out["metadata"]["found"] is False


def test_favor_curates_groups():
    rec = {
        "variant_vcf": "19-44908822-C-T", "rsid": "rs7412", "chromosome": "19",
        "position": "44908822", "genecode_comprehensive_info": "APOE",
        "genecode_comprehensive_category": "exonic", "cadd_phred": 25.3,
        "am_class": "ambiguous", "bravo_af": 0.0781, "af_total": 0.0788,
        "af_nfe": 0.0799, "clnsig": "drug_response", "gerp_s": 6.86,
    }
    with patch("tooluniverse.favor_tool.requests.get", return_value=_resp(200, rec)):
        out = _favor().run({"variant": "19-44908822-C-T"})
    assert out["status"] == "success"
    d = out["data"]
    assert d["found"] is True
    assert d["gene_consequence"]["gene"] == "APOE"
    assert d["deleteriousness"]["cadd_phred"] == 25.3
    assert d["allele_frequency"]["gnomad_af_by_ancestry"]["nfe"] == 0.0799
    assert d["clinical"]["clinvar_significance"] == "drug_response"
    assert d["all_annotations"] is rec  # full passthrough preserved


def test_favor_timeout_returns_error():
    with patch("tooluniverse.favor_tool.requests.get",
               side_effect=requests.exceptions.Timeout()):
        out = _favor().run({"variant": "19-44908822-C-T"})
    assert out["status"] == "error"
    assert "timed out" in out["error"]


# --------------------------------------------------------------------------- #
# OPSIN
# --------------------------------------------------------------------------- #
def _opsin():
    return OPSINNameToStructureTool(
        {"name": "OPSIN_name_to_structure", "type": "OPSINNameToStructureTool",
         "parameter": {"type": "object", "properties": {}}}
    )


def test_opsin_requires_name():
    out = _opsin().run({})
    assert out["status"] == "error"
    assert "name" in out["error"]


def test_opsin_success():
    body = {"status": "SUCCESS", "smiles": "C(C)(=O)OC1=C(C(=O)O)C=CC=C1",
            "stdinchi": "InChI=1S/C9H8O4/...", "stdinchikey": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"}
    with patch("tooluniverse.opsin_tool.requests.get", return_value=_resp(200, body)):
        out = _opsin().run({"name": "2-acetoxybenzoic acid"})
    assert out["status"] == "success"
    assert out["data"]["parsed"] is True
    assert out["data"]["smiles"].startswith("C(C)")
    assert out["data"]["inchikey"] == "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"


def test_opsin_unparseable_is_success_parsed_false():
    # OPSIN returns HTTP 404 + a FAILURE body for trade/trivial names.
    body = {"status": "FAILURE", "message": "aspirin was uninterpretable"}
    with patch("tooluniverse.opsin_tool.requests.get", return_value=_resp(404, body)):
        out = _opsin().run({"name": "aspirin"})
    assert out["status"] == "success"
    assert out["data"]["parsed"] is False
    assert out["data"]["smiles"] is None


# --------------------------------------------------------------------------- #
# NCBI Datasets genome assembly
# --------------------------------------------------------------------------- #
def _ncbi(endpoint_type):
    return NCBIDatasetsTool(
        {"name": f"NCBIDatasets_{endpoint_type}", "type": "NCBIDatasetsTool",
         "fields": {"endpoint_type": endpoint_type},
         "parameter": {"type": "object", "properties": {}}}
    )


def test_ncbi_summarize_assembly():
    report = {
        "accession": "GCF_000005845.2", "source_database": "SOURCE_DATABASE_REFSEQ",
        "organism": {"organism_name": "Escherichia coli str. K-12 substr. MG1655",
                     "tax_id": 511145, "infraspecific_names": {"strain": "K-12 substr. MG1655"}},
        "assembly_info": {"assembly_name": "ASM584v2", "assembly_level": "Complete Genome",
                          "refseq_category": "na", "release_date": "2013-09-26"},
        "assembly_stats": {"total_sequence_length": "4641652",
                           "total_number_of_chromosomes": 1, "gc_percent": 51},
    }
    s = NCBIDatasetsTool._summarize_assembly(report)
    assert s["accession"] == "GCF_000005845.2"
    assert s["organism_name"].startswith("Escherichia coli")
    assert s["strain"] == "K-12 substr. MG1655"
    assert s["assembly_level"] == "Complete Genome"
    assert s["gc_percent"] == 51


def test_ncbi_genome_assembly_requires_accession():
    out = _ncbi("genome_assembly").run({})
    assert out["status"] == "error"
    assert "accession" in out["error"]


def test_ncbi_list_genomes_by_taxon_dispatch():
    body = {"total_count": 466009, "reports": [
        {"accession": "GCF_000005845.2",
         "organism": {"organism_name": "Escherichia coli", "tax_id": 562},
         "assembly_info": {}, "assembly_stats": {}}]}
    with patch("tooluniverse.ncbi_datasets_tool.requests.get",
               return_value=_resp(200, body)):
        out = _ncbi("genomes_by_taxon").run({"taxon": "562", "limit": 1})
    assert out["status"] == "success"
    assert out["metadata"]["total_available"] == 466009
    assert out["data"][0]["accession"] == "GCF_000005845.2"


def test_ncbi_sequence_reports_curates():
    body = {"reports": [
        {"chr_name": "ANONYMOUS", "sequence_name": "Chromosome", "role": "assembled-molecule",
         "refseq_accession": "NC_000913.3", "genbank_accession": "U00096.3",
         "length": 4641652, "gc_percent": 50.5}]}
    with patch("tooluniverse.ncbi_datasets_tool.requests.get",
               return_value=_resp(200, body)):
        out = _ncbi("sequence_reports").run({"accession": "GCF_000005845.2"})
    assert out["status"] == "success"
    assert out["data"][0]["refseq_accession"] == "NC_000913.3"
    assert out["data"][0]["length"] == 4641652
