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
import tempfile

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


@pytest.mark.integration
@pytest.mark.skipif(not _has_rscript(), reason="Rscript not installed")
@pytest.mark.parametrize("operation", ["deseq2", "enrichgo"])
def test_results_remain_readable_after_r_exits(operation, tmp_path, monkeypatch):
    """Run the actual CSV writer in R; later runs must preserve earlier results."""
    import csv
    from pathlib import Path

    import tooluniverse.deseq2_tool as mod

    # Exercise quoting as well as the lifetime of the external output directory.
    output_dir = tmp_path / 'results with spaces " and 中文'
    output_dir.mkdir()
    monkeypatch.setattr(mod.tempfile, "tempdir", str(output_dir))
    input_file = tmp_path / "input.csv"
    input_file.write_text("placeholder\n")
    tool = DESeq2Tool.__new__(DESeq2Tool)
    real_run = tool._run_rscript

    def run_csv_writer(script):
        # Isolate file lifetime from statistical fitting so only base R is
        # needed. Execute the production save/announce fragment unchanged.
        writer = script.split("# Save full results\n", 1)[1]
        return real_run('res <- df <- data.frame(value=c(1, 2))\n' + writer)

    monkeypatch.setattr(tool, "_run_rscript", run_csv_writer)
    args = {
        "operation": operation,
        "counts_file": str(input_file),
        "metadata_file": str(input_file),
        "gene_list_file": str(input_file),
    }
    paths = []
    try:
        for _ in range(2):
            result = tool.run(args)
            assert result["status"] == "success", result
            path = Path(result["data"]["results_file"])
            paths.append(path)
            with path.open(newline="") as handle:
                rows = list(csv.DictReader(handle))
            assert [row["value"] for row in rows] == ["1", "2"]
        assert paths[0] != paths[1]
        assert paths[0].read_bytes() == paths[1].read_bytes()
    finally:
        for path in paths:
            path.unlink(missing_ok=True)


@pytest.mark.unit
@pytest.mark.parametrize("operation", ["deseq2", "enrichgo"])
def test_missing_results_file_is_an_error(operation, tmp_path, monkeypatch):
    """A zero R exit code must not make an unreadable result look successful."""
    input_file = tmp_path / "input.csv"
    input_file.write_text("placeholder\n")
    missing_file = tmp_path / "missing.csv"
    tool = DESeq2Tool.__new__(DESeq2Tool)
    monkeypatch.setattr(
        tool,
        "_run_rscript",
        lambda script: subprocess.CompletedProcess(
            args=[], returncode=0, stdout=f"RESULTS_FILE: {missing_file}\n", stderr=""
        ),
    )
    result = tool.run(
        {
            "operation": operation,
            "counts_file": str(input_file),
            "metadata_file": str(input_file),
            "gene_list_file": str(input_file),
        }
    )
    assert result["status"] == "error", result
    assert "Results file not found" in result["error"]


def _arguments(operation, tmp_path):
    input_file = tmp_path / "input.csv"
    input_file.write_text("placeholder\n")
    return {
        "operation": operation,
        "counts_file": str(input_file),
        "metadata_file": str(input_file),
        "gene_list_file": str(input_file),
    }


@pytest.mark.integration
@pytest.mark.skipif(not _has_rscript(), reason="Rscript not installed")
@pytest.mark.parametrize("operation", ["deseq2", "enrichgo"])
def test_results_are_not_readable_by_other_users(operation, tmp_path, monkeypatch):
    """A result that outlives R must not become readable to everyone.

    R's own session directory is mode 0700, so moving the CSV out of it to
    survive ``Rscript`` exiting can expose expression results to every other
    user of the machine. This runs the production writer with base R and
    checks the file R actually produced.
    """
    import stat

    tool = DESeq2Tool.__new__(DESeq2Tool)
    real_run = tool._run_rscript

    def run_csv_writer(script):
        writer = script.split("# Save full results\n", 1)[1]
        return real_run("res <- df <- data.frame(value=c(1, 2))\n" + writer)

    monkeypatch.setattr(tool, "_run_rscript", run_csv_writer)
    result = tool.run(_arguments(operation, tmp_path))
    assert result["status"] == "success", result
    results_file = result["data"]["results_file"]
    directory = os.path.dirname(results_file)
    try:
        # The temp root is world-writable by design, so the CSV cannot sit
        # directly in it; every directory below the root must be closed.
        assert directory != tempfile.gettempdir(), results_file
        while directory != tempfile.gettempdir():
            mode = stat.S_IMODE(os.stat(directory).st_mode)
            assert not mode & (stat.S_IRWXG | stat.S_IRWXO), (directory, oct(mode))
            directory = os.path.dirname(directory)
    finally:
        shutil.rmtree(os.path.dirname(results_file), ignore_errors=True)


@pytest.mark.unit
@pytest.mark.parametrize("operation", ["deseq2", "enrichgo"])
def test_a_failed_run_leaves_nothing_in_the_temp_root(operation, tmp_path, monkeypatch):
    """A run that produces no CSV must not leave its scratch space behind."""
    temp_root = tmp_path / "temp root"
    temp_root.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(temp_root))
    tool = DESeq2Tool.__new__(DESeq2Tool)
    monkeypatch.setattr(
        tool,
        "_run_rscript",
        lambda script: subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="R died"
        ),
    )
    result = tool.run(_arguments(operation, tmp_path))
    assert result["status"] == "error", result
    assert list(temp_root.iterdir()) == []
