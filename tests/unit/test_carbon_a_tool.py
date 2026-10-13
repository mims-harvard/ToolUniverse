"""Carbon-A annotation: the contract, without a GPU.

Everything here runs without the model, the pipeline or a CUDA device. The
provider subprocess is never started: either the arguments are refused before
it would be, or the pipeline's output files are faked on disk and only the
reading of them is exercised.

The live GPU run is a separate step, `scripts/remote_validation/
carbon_a_live_validation.py`, and what it measured is recorded in
`src/tooluniverse/remote/carbon_a/README.md`.
"""

import json
import os
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from tooluniverse.carbon_a_tool import (
    ATTN_ENV,
    INPUT_ROOT_ENV,
    JOB_ROOT_ENV,
    PIPELINE_ENV,
    CarbonATool,
)

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "src" / "tooluniverse"
INTERNAL_CONFIG = SOURCE_ROOT / "remote" / "carbon_a" / "carbon_a_client_tools.json"
PUBLISHED_CONFIG = SOURCE_ROOT / "data" / "remote_tools" / "carbon_a_tools.json"
SERVER_SOURCE = SOURCE_ROOT / "remote" / "carbon_a" / "carbon_a_mcp_server.py"

# Long enough to clear the pipeline's 100,000 bp record floor.
LONG_SEQUENCE = "ACGT" * 30_000  # 120,000 bp


def _config():
    return json.loads(INTERNAL_CONFIG.read_text(encoding="utf-8"))[0]


@pytest.fixture
def tool(tmp_path, monkeypatch):
    """A CarbonATool with a provider that looks configured but never runs."""
    pipeline = tmp_path / "annotation_pipeline" / "run_annotation.sh"
    pipeline.parent.mkdir(parents=True)
    pipeline.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    (pipeline.parent / "codon_tables").mkdir()
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    (inputs / "genome.fna").write_text(">x\nACGT\n", encoding="utf-8")
    monkeypatch.setenv(PIPELINE_ENV, str(pipeline))
    monkeypatch.setenv(INPUT_ROOT_ENV, str(inputs))
    monkeypatch.setenv(JOB_ROOT_ENV, str(tmp_path / "jobs"))
    (tmp_path / "jobs").mkdir()
    monkeypatch.delenv(ATTN_ENV, raising=False)
    return CarbonATool(tool_config=_config())


def _refused(result):
    assert result["status"] == "error", result
    return result["error"]


# --- the arguments the contract refuses --------------------------------------


def test_exactly_one_input_is_required(tool):
    for arguments in ({}, {"sequence": LONG_SEQUENCE, "input_file": "genome.fna"}):
        assert "exactly one" in _refused(tool.run(arguments))


def test_a_sequence_below_the_record_floor_is_refused_not_reported_empty(tool):
    """The pipeline skips a short record, so "no genes" would be a lie."""
    error = _refused(tool.run({"sequence": "ACGT" * 5_000}))  # 20,000 bp
    assert "20,000 bp" in error
    assert "100,000 bp" in error
    assert "skip the record" in error


def test_the_floor_can_be_lowered_deliberately(tool):
    result = tool.run(
        {"sequence": "ACGT" * 5_000, "min_record_length": 10_000, "dry_run": True}
    )
    assert result["status"] == "success"
    assert result["data"]["min_record_length"] == 10_000


def test_fasta_in_the_sequence_field_says_what_to_do_instead(tool):
    error = _refused(tool.run({"sequence": ">chr1\n" + LONG_SEQUENCE}))
    assert "not FASTA" in error
    assert "input_file" in error


def test_protein_in_the_sequence_field_is_refused(tool):
    assert "IUPAC nucleotide" in _refused(tool.run({"sequence": "MKVLAAGIVG" * 12_000}))


@pytest.mark.parametrize(
    "input_file",
    [
        "/etc/passwd",
        "../secret.fna",
        "sub/../../secret.fna",
        "https://example.com/genome.fna",
        "a,b.fna",
        "a" * 600,
    ],
)
def test_input_file_stays_inside_the_provider_directory(tool, input_file):
    assert _refused(tool.run({"input_file": input_file}))


def test_a_traversal_that_resolves_outside_is_refused_even_if_it_exists(
    tool, tmp_path, monkeypatch
):
    """The pattern allows dots; the realpath check is what stops this."""
    outside = tmp_path / "outside.fna"
    outside.write_text(">x\nACGT\n", encoding="utf-8")
    nested = tmp_path / "inputs" / "sub"
    nested.mkdir()
    monkeypatch.setenv(INPUT_ROOT_ENV, str(tmp_path / "inputs"))
    error = _refused(tool.run({"input_file": "sub/.../outside.fna"}))
    assert error


def test_a_missing_input_file_is_named_without_leaking_the_root(tool):
    error = _refused(tool.run({"input_file": "absent.fna"}))
    assert "absent.fna" in error
    assert os.environ[INPUT_ROOT_ENV] not in error


@pytest.mark.parametrize(
    "arguments",
    [
        {"min_confidence": 1.5},
        {"min_confidence": "high"},
        {"min_confidence": True},
        {"max_genes": 0},
        {"max_genes": 10_000},
        {"timeout_seconds": 0},
        {"timeout_seconds": 7_200},
        {"genetic_code": "table11"},
        {"attn_implementation": "xformers"},
        {"return_gff": "yes"},
        {"sequence_id": "has space"},
        {"sequence_id": "a" * 70},
        {"min_record_length": 0},
    ],
)
def test_out_of_contract_values_are_refused(tool, arguments):
    assert _refused(tool.run({"sequence": LONG_SEQUENCE, **arguments}))


def test_unknown_arguments_are_named(tool):
    error = _refused(tool.run({"sequence": LONG_SEQUENCE, "gpu_count": 4, "beam": 3}))
    assert "beam" in error and "gpu_count" in error


def test_a_provider_without_a_pipeline_says_so(tool, monkeypatch):
    monkeypatch.delenv(PIPELINE_ENV)
    assert PIPELINE_ENV in _refused(tool.run({"sequence": LONG_SEQUENCE}))


def test_an_input_file_without_a_configured_root_says_so(tool, monkeypatch):
    monkeypatch.delenv(INPUT_ROOT_ENV)
    error = _refused(tool.run({"input_file": "genome.fna"}))
    assert INPUT_ROOT_ENV in error


# --- the dry run ------------------------------------------------------------


def test_a_dry_run_reports_the_command_without_running_anything(tool):
    data = tool.run({"input_file": "genome.fna", "dry_run": True})["data"]
    assert data["dry_run"] is True
    command = data["command"]
    assert command[0] == "bash"
    assert "--min-record-length" in command
    assert "--codon-table" in command
    assert command[command.index("--codon-table") + 1].endswith("standard.json")


def test_the_genetic_code_selects_the_shipped_table(tool):
    data = tool.run(
        {
            "input_file": "genome.fna",
            "genetic_code": "tetrahymena_table6",
            "dry_run": True,
        }
    )["data"]
    table = data["command"][data["command"].index("--codon-table") + 1]
    assert table.endswith("GCF_000189635.1.json")
    assert data["genetic_code"] == "tetrahymena_table6"


def test_the_provider_sets_the_default_attention_implementation(tool, monkeypatch):
    monkeypatch.setenv(ATTN_ENV, "sdpa")
    data = tool.run({"input_file": "genome.fna", "dry_run": True})["data"]
    assert data["attn_implementation"] == "sdpa"
    data = tool.run(
        {
            "input_file": "genome.fna",
            "attn_implementation": "flash_attention_2",
            "dry_run": True,
        }
    )["data"]
    assert data["attn_implementation"] == "flash_attention_2"


def test_an_inline_sequence_is_described_by_length_not_content(tool):
    data = tool.run({"sequence": LONG_SEQUENCE, "dry_run": True})["data"]
    assert data["input"] == "inline sequence query (120,000 bp)"
    assert LONG_SEQUENCE[:40] not in json.dumps(data)


# --- reading what the pipeline wrote ----------------------------------------

# The real shape, copied from a live run's prediction.gff: confidence and
# status sit on the gene row, CDS rows parent the mRNA, and an mRNA id does not
# derive from its gene's id -- so the mRNA row is the only thing linking a CDS
# to a gene. An invented fixture that spelled mRNA ids as "gene1.1" hid that,
# and every exon count came out zero against real output.
GFF = """##gff-version 3
NC_001133.9\tCarbon-A\tgene\t100\t1200\t.\t+\t.\tID=gene000001;status=complete;confidence=0.874252
NC_001133.9\tCarbon-A\tmRNA\t100\t1200\t.\t+\t.\tID=mrna000001;Parent=gene000001
NC_001133.9\tCarbon-A\tCDS\t100\t600\t.\t+\t0\tID=mrna000001.cds;Parent=mrna000001
NC_001133.9\tCarbon-A\tCDS\t800\t1200\t.\t+\t2\tID=mrna000001.cds;Parent=mrna000001
NC_001133.9\tCarbon-A\tgene\t2000\t2500\t.\t-\t.\tID=gene000002;status=complete;confidence=0.040000
NC_001133.9\tCarbon-A\tmRNA\t2000\t2500\t.\t-\t.\tID=mrna000002;Parent=gene000002
NC_001133.9\tCarbon-A\tCDS\t2000\t2500\t.\t-\t0\tID=mrna000002.cds;Parent=mrna000002
NC_001134.8\tCarbon-A\tgene\t10\t900\t.\t+\t.\tID=gene000003;status=incomplete
NC_001134.8\tCarbon-A\tmRNA\t10\t900\t.\t+\t.\tID=mrna000003;Parent=gene000003
NC_001134.8\tCarbon-A\tCDS\t10\t900\t.\t+\t0\tID=mrna000003.cds;Parent=mrna000003
"""
# Protein records are named by the gene id, with the detail in the description.
FAA = """>gene000001 record_id=NC_001133.9 strand=+ loc=100-1200 aa_len=6 status=complete
MKVLAA
>gene000003 record_id=NC_001134.8 strand=+ loc=10-900 aa_len=4 status=incomplete
MQQW
"""


def _results(tmp_path, gff=GFF, faa=FAA, suffix=""):
    out = tmp_path / ("out" + suffix)
    out.mkdir()
    (out / "prediction.gff").write_text(gff, encoding="utf-8")
    if faa is not None:
        (out / "prediction.faa").write_text(faa, encoding="utf-8")
    return tmp_path / "out"


def _collect(tool, output_dir, **overrides):
    plan = {
        "min_confidence": 0.1,
        "max_genes": 200,
        "return_gff": False,
        "return_proteins": False,
        "genetic_code": "standard",
        "attn_implementation": "sdpa",
        "min_record_length": 100000,
        "input_description": "test",
    }
    plan.update(overrides)
    return tool._collect(plan, str(output_dir), 12.3)


def test_genes_below_min_confidence_are_counted_but_not_returned(tool, tmp_path):
    data = _collect(tool, _results(tmp_path))["data"]
    assert data["genes_predicted"] == 3
    assert data["genes_at_or_above_min_confidence"] == 2
    assert [gene["id"] for gene in data["genes"]] == ["gene000001", "gene000003"]


def test_a_gene_without_a_confidence_is_kept(tool, tmp_path):
    """Matching the pipeline's own reporting rule."""
    data = _collect(tool, _results(tmp_path), min_confidence=0.99)["data"]
    kept = {gene["id"]: gene["confidence"] for gene in data["genes"]}
    assert kept == {"gene000003": None}


def test_exons_coding_bases_and_records_are_counted(tool, tmp_path):
    data = _collect(tool, _results(tmp_path))["data"]
    gene1 = next(g for g in data["genes"] if g["id"] == "gene000001")
    assert gene1["exons"] == 2
    assert gene1["strand"] == "+"
    assert (gene1["start"], gene1["end"]) == (100, 1200)
    # 501 + 401 + 501 + 891 across all four CDS rows
    assert data["coding_bases"] == 501 + 401 + 501 + 891
    assert data["records_annotated"] == ["NC_001133.9", "NC_001134.8"]


def test_a_truncated_gene_is_flagged_from_the_status_attribute(tool, tmp_path):
    """utils.py writes status=complete|incomplete; nothing else marks it."""
    data = _collect(tool, _results(tmp_path), min_confidence=0.0)["data"]
    by_id = {gene["id"]: gene for gene in data["genes"]}
    assert by_id["gene000003"]["incomplete"] is True
    assert by_id["gene000001"]["incomplete"] is False


def test_exon_counts_come_through_the_mrna_row(tool, tmp_path):
    """A CDS parents the mRNA, whose id does not derive from the gene's.

    Counting by string-manipulating the Parent id gives every gene zero exons
    against real pipeline output.
    """
    data = _collect(tool, _results(tmp_path), min_confidence=0.0)["data"]
    exons = {gene["id"]: gene["exons"] for gene in data["genes"]}
    assert exons == {"gene000001": 2, "gene000002": 1, "gene000003": 1}
    assert all(count > 0 for count in exons.values())


def test_proteins_are_matched_to_genes_through_the_mrna_id(tool, tmp_path):
    data = _collect(tool, _results(tmp_path), return_proteins=True)["data"]
    by_id = {gene["id"]: gene for gene in data["genes"]}
    assert by_id["gene000001"]["protein"] == "MKVLAA"
    assert by_id["gene000001"]["protein_length"] == 6
    assert by_id["gene000003"]["protein"] == "MQQW"


def test_proteins_are_omitted_unless_asked_for(tool, tmp_path):
    data = _collect(tool, _results(tmp_path))["data"]
    assert all("protein" not in gene for gene in data["genes"])
    assert all("protein_length" in gene for gene in data["genes"])


def test_max_genes_caps_the_list_and_says_so(tool, tmp_path):
    data = _collect(tool, _results(tmp_path), max_genes=1)["data"]
    assert data["genes_returned"] == 1
    assert data["genes_at_or_above_min_confidence"] == 2
    assert "1 of 2" in data["genes_note"]


def test_the_gff_is_returned_only_when_asked_for(tool, tmp_path):
    out = _results(tmp_path)
    assert "gff" not in _collect(tool, out)["data"]
    assert "##gff-version 3" in _collect(tool, out, return_gff=True)["data"]["gff"]


def test_a_pipeline_that_wrote_nothing_is_an_error_not_an_empty_success(
    tool, monkeypatch
):
    """Through run(), so the provider failure becomes a caller-facing error.

    A pipeline that exits 0 and writes no prediction must not be reported as a
    genome with no genes in it.
    """
    monkeypatch.setattr(
        CarbonATool, "_run_pipeline", lambda self, plan, inp, out, wd: None
    )
    result = tool.run({"sequence": LONG_SEQUENCE})
    assert result["status"] == "error"
    assert "no output directory" in result["error"]


def test_a_run_that_produced_no_gff_is_an_error(tool, monkeypatch):
    def write_empty_dir(self, plan, input_path, output_dir, workdir):
        os.makedirs(output_dir)

    monkeypatch.setattr(CarbonATool, "_run_pipeline", write_empty_dir)
    result = tool.run({"sequence": LONG_SEQUENCE})
    assert result["status"] == "error"
    assert "prediction.gff" in result["error"]


def test_run_writes_the_inline_sequence_as_fasta_for_the_pipeline(tool, monkeypatch):
    """What the pipeline receives is a FASTA file named by sequence_id."""
    seen = {}

    def capture(self, plan, input_path, output_dir, workdir):
        seen["text"] = Path(input_path).read_text(encoding="ascii")
        os.makedirs(output_dir)
        (Path(output_dir) / "prediction.gff").write_text(GFF, encoding="utf-8")

    monkeypatch.setattr(CarbonATool, "_run_pipeline", capture)
    result = tool.run({"sequence": LONG_SEQUENCE, "sequence_id": "scaffold_7"})
    assert result["status"] == "success"
    assert seen["text"].startswith(">scaffold_7\n")
    assert "".join(seen["text"].split("\n")[1:]) == LONG_SEQUENCE
    assert result["data"]["sequence_length"] == 120_000


def test_a_flagged_codon_table_returns_the_genes_with_the_warning(tool, tmp_path):
    """The pipeline renames its output directory on a likely mismatch."""
    _results(tmp_path, suffix="_WARNING")
    (tmp_path / "WARNINGS.txt").write_text(
        "GCF_000189635.1: only 3% of genes reached confidence 0.1\n", encoding="utf-8"
    )
    result = _collect(tool, tmp_path / "out")
    assert result["status"] == "success"
    data = result["data"]
    assert data["genes_returned"] == 2
    warnings = " ".join(data["warnings"])
    assert "may not fit" in warnings
    assert "only 3%" in warnings


def test_an_unflagged_run_carries_no_warnings(tool, tmp_path):
    assert "warnings" not in _collect(tool, _results(tmp_path))["data"]


def test_results_without_proteins_still_report_genes(tool, tmp_path):
    data = _collect(tool, _results(tmp_path, faa=None))["data"]
    assert data["genes_returned"] == 2
    assert all("protein_length" not in gene for gene in data["genes"])


# --- the published contract -------------------------------------------------


def test_the_internal_and_published_schemas_agree():
    internal = json.loads(INTERNAL_CONFIG.read_text(encoding="utf-8"))
    published = json.loads(PUBLISHED_CONFIG.read_text(encoding="utf-8"))
    assert [item["name"] for item in internal] == [item["name"] for item in published]
    assert internal[0]["parameter"] == published[0]["parameter"]
    assert internal[0]["return_schema"] == published[0]["return_schema"]
    assert internal[0]["description"] == published[0]["description"]
    assert internal[0]["type"] == "CarbonATool"
    assert published[0]["type"] == "RemoteTool"


def test_the_published_schema_is_closed_and_valid():
    published = json.loads(PUBLISHED_CONFIG.read_text(encoding="utf-8"))[0]
    Draft202012Validator.check_schema(published["parameter"])
    Draft202012Validator.check_schema(published["return_schema"])
    assert published["parameter"]["additionalProperties"] is False


def test_every_tool_argument_is_a_server_parameter():
    """A parameter the server does not accept is advertised and unusable."""
    published = json.loads(PUBLISHED_CONFIG.read_text(encoding="utf-8"))[0]
    source = SERVER_SOURCE.read_text(encoding="utf-8")
    for name in published["parameter"]["properties"]:
        assert f"{name}: Annotated[" in source, name
    assert 'TOOLUNIVERSE_MCP_PORT", "8034"' in source


def test_the_loader_points_at_the_same_port():
    loader = json.loads(
        (SOURCE_ROOT / "data" / "carbon_a_mcp_loader_tools.json").read_text(
            encoding="utf-8"
        )
    )[0]
    assert loader["server_url"].endswith(":8034/mcp")
    assert loader["required_api_keys"] == ["CARBON_A_MCP_SERVER_HOST"]
