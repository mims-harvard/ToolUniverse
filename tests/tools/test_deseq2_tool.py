"""Unit tests for DESeq2Tool (deseq2_tool.py).

Primary purpose: guard the enrichgo backslash-escape regression. The tool builds
R code containing the Ensembl-version strip ``sub("\\..*", "", genes)`` (two
backslashes in the generated R source). When that code was executed via
``Rscript -e <string>``, R collapsed one backslash level and aborted with
"'\\.' is an unrecognized escape in character string". The fix runs R from a
temp script file instead, which is parsed verbatim. These tests pin that
behavior and the surrounding error handling.
"""

import os
import shutil
import subprocess

import pytest

from tooluniverse.deseq2_tool import DESeq2Tool

# The exact Ensembl-strip regex the tool generates: two backslashes in R source.
_BACKSLASH_R_CODE = 'cat("OUT:", sub("\\\\..*", "", "ENSG00000103196.7"), "\\n")\n'


def _has_rscript():
    return shutil.which("Rscript") is not None


@pytest.mark.skipif(not _has_rscript(), reason="Rscript not installed")
def test_run_rscript_preserves_backslash_regex():
    """The fix: file-based execution keeps the regex intact (the failing case)."""
    r = DESeq2Tool._run_rscript(_BACKSLASH_R_CODE)
    assert r.returncode == 0, f"R failed: {r.stderr}"
    assert "OUT: ENSG00000103196" in r.stdout


@pytest.mark.skipif(not _has_rscript(), reason="Rscript not installed")
def test_minus_e_invocation_is_what_broke():
    """Documents the root cause: the same code via ``Rscript -e`` is rejected,
    proving the file-based path is required, not incidental."""
    r = subprocess.run(
        ["Rscript", "-e", _BACKSLASH_R_CODE], capture_output=True, text=True
    )
    assert r.returncode != 0
    assert "unrecognized escape" in r.stderr


def test_run_rscript_cleans_up_temp_file(monkeypatch):
    """The temp .R file is always removed, even when Rscript is absent."""
    import tooluniverse.deseq2_tool as mod

    created = {}
    real_named = mod.tempfile.NamedTemporaryFile

    def spy(*a, **k):
        f = real_named(*a, **k)
        created["path"] = f.name
        return f

    monkeypatch.setattr(mod.tempfile, "NamedTemporaryFile", spy)
    try:
        DESeq2Tool._run_rscript('cat("ok")\n')
    except FileNotFoundError:
        pass  # Rscript not installed; cleanup must still have run

    assert "path" in created
    assert not os.path.exists(created["path"]), "temp .R file was not cleaned up"


def test_unknown_operation():
    tool = DESeq2Tool.__new__(DESeq2Tool)
    res = tool.run({"operation": "does_not_exist"})
    assert res["status"] == "error"
    assert "Unknown operation" in res["error"]


def test_deseq2_missing_input_files():
    tool = DESeq2Tool.__new__(DESeq2Tool)
    res = tool.run(
        {
            "operation": "deseq2",
            "counts_file": "/no/such/counts.csv",
            "metadata_file": "/no/such/meta.csv",
        }
    )
    assert res["status"] == "error"
    assert "not found" in res["error"]


def test_enrichgo_missing_gene_list():
    tool = DESeq2Tool.__new__(DESeq2Tool)
    res = tool.run(
        {"operation": "enrichgo", "gene_list_file": "/no/such/genes.txt"}
    )
    assert res["status"] == "error"
    assert "not found" in res["error"]
