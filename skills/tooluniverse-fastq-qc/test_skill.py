#!/usr/bin/env python3
"""Tests for tooluniverse-fastq-qc skill.

Focus: the preflight contract. When a required binary (FastQC) is absent
from PATH, run_fastq_qc.py must (a) print an install plan, (b) NOT fabricate
QC results, and (c) exit 0 (clean "cannot run yet").

These tests run with no QC binaries installed, which is the realistic CI
environment, so we simulate "missing" by pointing PATH at an empty dir.
"""

import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "scripts", "run_fastq_qc.py")


def _run_with_empty_path(extra_args):
    """Run the orchestrator with an empty PATH so all binaries appear missing."""
    empty = tempfile.mkdtemp(prefix="empty_path_")
    env = dict(os.environ)
    env["PATH"] = empty  # nothing resolvable -> shutil.which returns None
    fastq = os.path.join(tempfile.mkdtemp(prefix="reads_"), "sample_R1.fastq.gz")
    open(fastq, "w").close()  # input existence is irrelevant; preflight runs first
    workdir = tempfile.mkdtemp(prefix="qc_out_")
    cmd = [sys.executable, SCRIPT, "--fastq", fastq, "--workdir", workdir] + extra_args
    return subprocess.run(cmd, capture_output=True, text=True, env=env), workdir


def test_preflight_exits_zero_when_tools_missing():
    proc, _ = _run_with_empty_path([])
    assert proc.returncode == 0, f"expected exit 0, got {proc.returncode}\n{proc.stderr}"


def test_preflight_prints_install_plan():
    proc, _ = _run_with_empty_path([])
    out = proc.stdout
    assert "PREFLIGHT" in out
    assert "INSTALL PLAN" in out
    assert "bioconda" in out
    assert "fastqc" in out
    print("install plan emitted correctly")


def test_preflight_does_not_fabricate_results():
    proc, workdir = _run_with_empty_path([])
    out = proc.stdout
    # No QC numbers should ever appear when tools are missing.
    assert "PASS" not in out and "FAIL" not in out
    assert "per-base quality:" not in out.lower()
    # Workdir must contain no fastqc / trimmed outputs.
    produced = []
    for root, _dirs, files in os.walk(workdir):
        produced.extend(files)
    assert produced == [], f"workdir should be empty, found {produced}"
    print("no results fabricated; workdir clean")


def test_trim_mode_also_requires_fastp():
    proc, _ = _run_with_empty_path(["--mode", "trim"])
    assert proc.returncode == 0
    assert "fastp" in proc.stdout  # listed as a missing required tool


def test_refuses_workdir_equal_to_input_dir():
    """Workspace isolation guard (only reachable when tools are present;
    here we just assert the helper logic directly)."""
    sys.path.insert(0, os.path.join(HERE, "scripts"))
    import run_fastq_qc as r
    indir = tempfile.mkdtemp(prefix="in_")
    f = os.path.join(indir, "r.fastq")
    open(f, "w").close()
    # available tools faked present so we reach the isolation check
    try:
        r.assert_workdir_isolated(indir, [f])
        raise AssertionError("should have refused workdir==input dir")
    except SystemExit as e:
        assert e.code == 2
    print("workspace isolation guard works")


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except Exception as e:  # noqa: BLE001
                failures += 1
                print(f"FAIL {name}: {e}")
    print(f"\n{'ALL PASS' if failures == 0 else str(failures) + ' FAILED'}")
    sys.exit(1 if failures else 0)
