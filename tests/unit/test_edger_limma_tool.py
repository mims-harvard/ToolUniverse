"""Unit tests for the edgeR / limma-voom DE tool (Rscript-backed).

The live runs need Rscript + Bioconductor edgeR/limma, so they skip when those
are absent (mirroring the bcftools guard). A synthetic dataset with a known set
of differentially-expressed genes is generated per test; the tests assert the
tool recovers them. Validation and error paths run without R.
"""

import csv
import random
import shutil

import pytest

from tooluniverse.edger_limma_tool import EdgeRLimmaTool

pytestmark = pytest.mark.unit

HAS_RSCRIPT = shutil.which("Rscript") is not None
needs_r = pytest.mark.skipif(not HAS_RSCRIPT, reason="Rscript not installed")


def _tool():
    return EdgeRLimmaTool(
        {"name": "de", "type": "EdgeRLimmaTool",
         "parameter": {"type": "object", "properties": {}}}
    )


def _make_dataset(tmp_path, n_de=30, n_genes=300):
    """Write counts.csv + meta.csv; the first n_de genes are up in 'treated'."""
    rng = random.Random(0)
    samples = ["t1", "t2", "t3", "c1", "c2", "c3"]
    cond = ["treated"] * 3 + ["control"] * 3
    counts = tmp_path / "counts.csv"
    meta = tmp_path / "meta.csv"
    with open(counts, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["gene"] + samples)
        for g in range(n_genes):
            base = rng.randint(50, 500)
            row = [f"G{g}"]
            for sample_cond in cond:
                mu = base * (3.0 if (g < n_de and sample_cond == "treated") else 1.0)
                row.append(max(0, int(rng.gauss(mu, mu * 0.25))))
            w.writerow(row)
    with open(meta, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["sample", "condition"])
        for s, c in zip(samples, cond):
            w.writerow([s, c])
    return str(counts), str(meta)


def _maybe_skip_no_packages(out):
    if out["status"] == "error" and (
        "edgeR" in out["error"] or "package" in out["error"] or "limma" in out["error"]
    ):
        pytest.skip("Bioconductor edgeR/limma not installed")


@needs_r
@pytest.mark.parametrize("method", ["edger", "limma"])
def test_recovers_planted_de_genes(tmp_path, method):
    """Both methods recover the planted DE genes (about 30) and rank them sig."""
    counts, meta = _make_dataset(tmp_path)
    out = _tool().run({
        "counts_file": counts, "metadata_file": meta, "design": "~ condition",
        "contrast": "condition,treated,control", "method": method,
        "report_genes": "G0,G250",
    })
    _maybe_skip_no_packages(out)
    assert out["status"] == "success"
    d = out["data"]
    assert d["method"] == method
    assert d["n_genes"] == 300
    assert 25 <= d["sig_padj_only"] <= 35  # ~30 planted
    assert d["gene_report"]["G0"]["FDR"] < 0.05  # true DE
    assert d["gene_report"]["G250"]["FDR"] > 0.05  # null gene


# --- validation / error paths (no R needed) -------------------------------- #
def test_bad_method_is_error():
    """method must be edger or limma."""
    out = _tool().run({"counts_file": "/tmp/x.csv", "metadata_file": "/tmp/m.csv",
                       "contrast": "condition,a,b", "method": "deseq2"})
    assert out["status"] == "error" and "edger" in out["error"]


def test_missing_counts_is_error():
    """A nonexistent counts file is a clean error."""
    out = _tool().run({"counts_file": "/no/such.csv", "metadata_file": "/no/such2.csv",
                       "contrast": "condition,a,b", "method": "edger"})
    assert out["status"] == "error" and "Counts file" in out["error"]


def test_bad_contrast_is_error(tmp_path):
    """Contrast must be 'factor,level1,level2'."""
    counts, meta = _make_dataset(tmp_path, n_de=1, n_genes=5)
    out = _tool().run({"counts_file": counts, "metadata_file": meta,
                       "contrast": "condition_treated", "method": "edger"})
    assert out["status"] == "error" and "contrast" in out["error"]
