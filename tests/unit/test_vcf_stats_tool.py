"""Unit tests for the canonical VCF statistics tool (bcftools-backed).

The live operations need the ``bcftools`` binary, so they are skipped when it
is absent. The pure parser (``_parse_stats``) is tested unconditionally.

The fixture VCF deliberately contains two multiallelic sites and a low-quality
record so the tests pin the behaviours that motivated the tool: deterministic
SNP/indel counting, filter handling, and the count change after splitting
multiallelics with ``bcftools norm``.
"""

import shutil
import textwrap

import pytest

from tooluniverse.vcf_stats_tool import VCFStatsTool, _parse_stats

pytestmark = pytest.mark.unit

HAS_BCFTOOLS = shutil.which("bcftools") is not None
needs_bcftools = pytest.mark.skipif(not HAS_BCFTOOLS, reason="bcftools not installed")

_VCF = textwrap.dedent(
    """\
    ##fileformat=VCFv4.2
    ##FILTER=<ID=PASS,Description="passed">
    ##FILTER=<ID=LowQual,Description="low quality">
    ##contig=<ID=chr1,length=2000>
    ##INFO=<ID=DP,Number=1,Type=Integer,Description="depth">
    ##FORMAT=<ID=GT,Number=1,Type=String,Description="genotype">
    #CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tS1\tS2
    chr1\t100\t.\tA\tG\t50\tPASS\tDP=30\tGT\t0/1\t1/1
    chr1\t150\t.\tA\tG,T\t60\tPASS\tDP=40\tGT\t1/2\t0/1
    chr1\t200\t.\tC\tCTT\t45\tPASS\tDP=25\tGT\t0/1\t0/0
    chr1\t300\t.\tGAT\tG\t40\tPASS\tDP=20\tGT\t1/1\t0/1
    chr1\t400\t.\tT\tC\t12\tLowQual\tDP=8\tGT\t0/1\t./.
    chr1\t500\t.\tATG\tA,ATGTG\t35\tPASS\tDP=22\tGT\t1/2\t0/0
    """
)


def _tool():
    return VCFStatsTool({"name": "vcf", "type": "VCFStatsTool",
                         "parameter": {"type": "object", "properties": {}}})


@pytest.fixture()
def vcf_path(tmp_path):
    p = tmp_path / "sample.vcf"
    p.write_text(_VCF)
    return str(p)


# --------------------------------------------------------------------------- #
# Pure parser (no bcftools needed)
# --------------------------------------------------------------------------- #
def test_parse_stats_extracts_summary_tstv_and_psc():
    sample = textwrap.dedent(
        """\
        SN\t0\tnumber of records:\t6
        SN\t0\tnumber of SNPs:\t3
        SN\t0\tnumber of indels:\t3
        SN\t0\tnumber of MNPs:\t0
        SN\t0\tnumber of multiallelic sites:\t2
        SN\t0\tnumber of samples:\t2
        TSTV\t0\t3\t1\t3.00\t3\t1\t3.00
        PSC\t0\tS1\t0\t0\t3\t2\t1\t3\t30.0\t0\t0\t0\t0
        """
    )
    out = _parse_stats(sample)
    assert out["records"] == 6
    assert out["snps"] == 3
    assert out["indels"] == 3
    assert out["multiallelic_sites"] == 2
    assert out["ts_tv"]["ts_tv_ratio"] == 3.0
    assert out["per_sample"][0]["sample"] == "S1"
    assert out["per_sample"][0]["nHets"] == 3


# --------------------------------------------------------------------------- #
# Error handling (no bcftools needed beyond the missing-binary guard)
# --------------------------------------------------------------------------- #
@needs_bcftools
def test_missing_vcf_path_returns_error():
    """summary_stats without vcf_path is a clean error, not a crash."""
    out = _tool().run({"operation": "summary_stats"})
    assert out["status"] == "error" and "vcf_path" in out["error"]


@needs_bcftools
def test_file_not_found_returns_error():
    """A nonexistent path returns a 'not found' error dict."""
    out = _tool().run({"operation": "summary_stats", "vcf_path": "/no/such/file.vcf"})
    assert out["status"] == "error" and "not found" in out["error"]


@needs_bcftools
def test_unknown_operation_returns_error():
    """An unrecognized operation returns an error naming 'operation'."""
    out = _tool().run({"operation": "bogus", "vcf_path": "/tmp/x.vcf"})
    assert out["status"] == "error" and "operation" in out["error"]


# --------------------------------------------------------------------------- #
# Live operations
# --------------------------------------------------------------------------- #
@needs_bcftools
def test_summary_stats_counts(vcf_path):
    """Canonical SNP/indel/multiallelic counts for the fixture VCF."""
    out = _tool().run({"operation": "summary_stats", "vcf_path": vcf_path})
    assert out["status"] == "success"
    d = out["data"]
    assert d["records"] == 6
    assert d["snps"] == 3
    assert d["indels"] == 3
    assert d["multiallelic_sites"] == 2
    assert {s["sample"] for s in d["per_sample"]} == {"S1", "S2"}


@needs_bcftools
def test_count_variants_filter_drops_lowqual(vcf_path):
    """PASS-only + min_qual must exclude the LowQual/QUAL=12 record."""
    # The QUAL=12 / LowQual record at chr1:400 must be excluded by both filters.
    out = _tool().run({
        "operation": "count_variants", "vcf_path": vcf_path,
        "pass_only": True, "min_qual": 30,
    })
    assert out["status"] == "success"
    assert out["data"]["records"] == 5
    assert out["data"]["filters_applied"] == {"pass_only": True, "min_qual": 30}


@needs_bcftools
def test_normalize_split_changes_indel_count(vcf_path):
    """Splitting multiallelics adds records and one indel (the key gap)."""
    # Splitting the two multiallelic sites adds two records and one indel —
    # the exact discrepancy an ad-hoc parser misses.
    out = _tool().run({
        "operation": "normalize", "vcf_path": vcf_path, "multiallelics": "split",
    })
    assert out["status"] == "success"
    assert out["data"]["before"]["records"] == 6
    assert out["data"]["after"]["records"] == 8
    assert out["data"]["after"]["indels"] == 4
    assert out["data"]["left_aligned"] is False
