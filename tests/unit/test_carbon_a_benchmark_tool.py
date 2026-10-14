"""The Carbon-A benchmark collection tools, without the network.

The bucket is stubbed, so these cover the joining and reporting: grouping a
flat file listing into genomes, attaching organisms, labelling file roles,
summarizing a sequence report, and what happens when the bucket is down,
truncates its listing, or is asked for an accession it does not have.

The organism map is checked for shape only. It was built one accession per
request against NCBI with the bucket's own file names as a cross-check -- a
single batched request came back mis-keyed -- and re-verifying 41 live lookups
does not belong in a unit test.
"""

import json

import pytest
import requests

from tooluniverse.carbon_a_benchmark_tool import (
    _ORGANISMS,
    BUCKET,
    SPLITS,
    CarbonABenchmarkTool,
)

pytestmark = pytest.mark.unit


TREE = [
    {
        "path": "eval/seen/GCF_000146045.2/GCF_000146045.2_R64_genomic.fna",
        "size": 12310392,
    },
    {"path": "eval/seen/GCF_000146045.2/genomic.gff", "size": 12437498},
    {"path": "eval/seen/GCF_000146045.2/cds_from_genomic.fna", "size": 10217356},
    {"path": "eval/seen/GCF_000146045.2/protein.faa", "size": 100},
    {"path": "eval/seen/GCF_000146045.2/md5sum.txt", "size": 667},
    {"path": "eval/seen/GCF_000146045.2/sequence_report.jsonl", "size": 5474},
    {
        "path": "eval/unseen/GCF_905368555.1/GCF_905368555.1_mMelGal1_genomic.fna",
        "size": 500,
    },
    {"path": "eval/unseen/GCF_905368555.1/genomic.gff", "size": 400},
    {
        "path": (
            "eval/nonstandard_code/GCF_000189635.1/"
            "GCF_000189635.1_JCVI-TTA1-2.2_genomic.fna"
        ),
        "size": 104425347,
    },
    # Not a genome directory: must be ignored rather than become one.
    {"path": "eval/README.md", "size": 10},
]

MD5SUM = (
    "496ffd6818c62eb443972a0e6c96bf5d  "
    "ncbi_dataset/data/GCF_000146045.2/GCF_000146045.2_R64_genomic.fna\n"
    "86761689e652f6b2223017ddc3743e33  "
    "ncbi_dataset/data/GCF_000146045.2/genomic.gff\n"
)

SEQUENCE_REPORT = "\n".join(
    json.dumps(row)
    for row in (
        {
            "chrName": "II",
            "length": 813184,
            "refseqAccession": "NC_001134.8",
            "gcPercent": 38.5,
            "role": "assembled-molecule",
        },
        {
            "chrName": "I",
            "length": 230218,
            "refseqAccession": "NC_001133.9",
            "gcPercent": 39.5,
            "role": "assembled-molecule",
        },
        {
            "chrName": "MT",
            "length": 85779,
            "refseqAccession": "NC_001224.1",
            "gcPercent": 17.1,
            "role": "assembled-molecule",
        },
    )
)


def _tool(operation, tree=TREE, md5=MD5SUM, report=SEQUENCE_REPORT):
    tool = CarbonABenchmarkTool(
        tool_config={
            "name": "t",
            "type": "CarbonABenchmarkTool",
            "fields": {"operation": operation},
        }
    )

    def fake_get(url, as_json, timeout=None):
        if as_json:
            return tree
        if url.endswith("md5sum.txt"):
            if md5 is None:
                raise requests.exceptions.ConnectionError("no md5")
            return md5
        if url.endswith("sequence_report.jsonl"):
            if report is None:
                raise requests.exceptions.ConnectionError("no report")
            return report
        raise AssertionError(f"unexpected fetch: {url}")

    tool._get = fake_get
    return tool


# --- listing ----------------------------------------------------------------


def test_the_listing_groups_files_into_genomes():
    data = _tool("list_genomes").run({})["data"]
    assert data["total_in_collection"] == 3
    assert data["counts_by_split"] == {"seen": 1, "unseen": 1, "nonstandard_code": 1}
    yeast = next(g for g in data["genomes"] if g["accession"] == "GCF_000146045.2")
    assert yeast["organism"] == "Saccharomyces cerevisiae S288C"
    assert yeast["tax_id"] == 559292
    assert yeast["assembly_name"] == "R64"
    assert yeast["genome_fasta_bytes"] == 12310392
    assert yeast["files"] == 6


def test_a_path_that_is_not_a_genome_directory_is_ignored():
    data = _tool("list_genomes").run({})["data"]
    assert "README.md" not in {g["accession"] for g in data["genomes"]}


def test_the_split_filter_selects_one_subdirectory():
    data = _tool("list_genomes").run({"split": "unseen"})["data"]
    assert [g["accession"] for g in data["genomes"]] == ["GCF_905368555.1"]
    assert data["count"] == 1
    assert data["total_in_collection"] == 3


def test_an_unknown_split_is_refused_and_names_the_valid_ones():
    result = _tool("list_genomes").run({"split": "test"})
    assert result["status"] == "error"
    for split in SPLITS:
        assert split in result["error"]


def test_the_organism_filter_is_a_case_insensitive_substring():
    data = _tool("list_genomes").run({"organism_contains": "saccharomyces"})["data"]
    assert [g["accession"] for g in data["genomes"]] == ["GCF_000146045.2"]
    empty = _tool("list_genomes").run({"organism_contains": "Mus musculus"})["data"]
    assert empty["genomes"] == []
    assert empty["count"] == 0


def test_a_listing_at_the_page_limit_says_it_may_be_incomplete():
    big = [
        {"path": f"eval/seen/GCF_{index:09d}.1/genomic.gff", "size": 1}
        for index in range(1000)
    ]
    data = _tool("list_genomes", tree=big).run({})["data"]
    assert "may be incomplete" in data["truncated"]


# --- one genome -------------------------------------------------------------


def test_a_genome_reports_urls_checksums_and_roles():
    data = _tool("get_genome").run({"accession": "GCF_000146045.2"})["data"]
    assert data["organism"] == "Saccharomyces cerevisiae S288C"
    assert data["split"] == "seen"
    assert data["download_url_base"].endswith("/eval/seen/GCF_000146045.2")
    by_name = {f["filename"]: f for f in data["files"]}
    genome = by_name["GCF_000146045.2_R64_genomic.fna"]
    assert genome["md5"] == "496ffd6818c62eb443972a0e6c96bf5d"
    assert genome["url"] == f"{data['download_url_base']}/{genome['filename']}"
    assert genome["role"] == "Genomic DNA, the input to annotation."
    # cds_from_genomic.fna also ends in _genomic.fna and is not the genome.
    assert by_name["cds_from_genomic.fna"]["role"].startswith("Reference CDS")
    assert by_name["genomic.gff"]["role"].startswith("NCBI reference annotation")
    assert by_name["protein.faa"]["md5"] is None


def test_the_sequence_report_is_summarized_longest_first():
    report = _tool("get_genome").run({"accession": "GCF_000146045.2"})["data"][
        "sequence_report"
    ]
    assert report["available"] is True
    assert report["sequences_in_assembly"] == 3
    assert report["total_length_bp"] == 813184 + 230218 + 85779
    assert [s["name"] for s in report["sequences"]] == ["II", "I", "MT"]
    assert report["roles"] == {"assembled-molecule": 3}


def test_the_sequence_report_can_be_skipped():
    data = _tool("get_genome").run(
        {"accession": "GCF_000146045.2", "include_sequence_report": False}
    )["data"]
    assert "sequence_report" not in data


def test_the_nonstandard_code_genome_warns_about_its_translation_table():
    data = _tool("get_genome").run({"accession": "GCF_000189635.1"})["data"]
    assert "table 6" in data["genetic_code_note"]
    assert data["organism"] == "Tetrahymena thermophila SB210"


def test_a_standard_code_genome_carries_no_such_note():
    data = _tool("get_genome").run({"accession": "GCF_000146045.2"})["data"]
    assert "genetic_code_note" not in data


def test_an_unknown_accession_says_how_to_find_the_real_ones():
    result = _tool("get_genome").run({"accession": "GCF_000000000.1"})
    assert result["status"] == "error"
    assert "Carbon_A_list_benchmark_genomes" in result["error"]
    assert "3 genomes" in result["error"]


def test_a_missing_accession_argument_is_refused():
    result = _tool("get_genome").run({})
    assert result["status"] == "error"
    assert "accession is required" in result["error"]


def test_an_unreadable_checksum_file_does_not_fail_the_call():
    data = _tool("get_genome", md5=None).run({"accession": "GCF_000146045.2"})["data"]
    assert all(f["md5"] is None for f in data["files"])
    assert data["organism"] == "Saccharomyces cerevisiae S288C"


def test_an_unreadable_sequence_report_is_reported_as_unavailable():
    report = _tool("get_genome", report=None).run({"accession": "GCF_000146045.2"})[
        "data"
    ]["sequence_report"]
    assert report["available"] is False
    assert "could not be read" in report["error"]


# --- the bucket being down --------------------------------------------------


@pytest.mark.parametrize("operation", ["list_genomes", "get_genome"])
def test_a_timeout_names_the_bucket(operation):
    tool = _tool(operation)

    def boom(url, as_json, timeout=None):
        raise requests.exceptions.Timeout()

    tool._get = boom
    result = tool.run({"accession": "GCF_000146045.2"})
    assert result["status"] == "error"
    assert BUCKET in result["error"]


def test_an_http_error_distinguishes_a_visibility_change():
    tool = _tool("list_genomes")

    class _Response:
        status_code = 403

    def boom(url, as_json, timeout=None):
        raise requests.exceptions.HTTPError(response=_Response())

    tool._get = boom
    result = tool.run({})
    assert "403" in result["error"]
    assert "visibility" in result["error"]


def test_an_unknown_operation_is_refused():
    tool = _tool("list_genomes")
    tool.operation = "delete_everything"
    assert tool.run({})["status"] == "error"


# --- the shipped organism map ----------------------------------------------


def test_the_organism_map_covers_the_collection_and_is_well_formed():
    assert len(_ORGANISMS) == 41
    for accession, (organism, tax_id) in _ORGANISMS.items():
        assert accession.startswith("GCF_"), accession
        assert organism and organism[0].isupper(), accession
        assert isinstance(tax_id, int) and tax_id > 0, accession


def test_the_map_has_no_duplicate_accessions_with_conflicting_taxa():
    """Two accessions may share an organism; one accession may not have two."""
    assert len(set(_ORGANISMS)) == len(_ORGANISMS)
