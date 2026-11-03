"""Shipped skills must not carry a worked solution to a benchmark item.

Issue #844: a reference under `tooluniverse-image-analysis` held a step-by-step
solution to BixBench bix-54 -- the capsule's input file, its column names, the
rows to drop, the model to fit and the quantities to read off -- so an agent
loading that skill while being scored on BixBench was handed the item's answer.

The repo already had a detector for this, `check_memorization.py`, and it
reported zero failures over the leak for two reasons, both of which this test
closes:

  * it was a script nothing ran automatically, so it only ever reported what
    someone remembered to ask it about; and
  * `--all` walked `skills/` alone, while the copies that are redistributed
    live under `plugin/skills/` and `plugins/tooluniverse/skills/`.

Running it here, over all three roots, makes the guard a condition of merging
rather than a courtesy check.
"""

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
CHECKER = (
    REPO / "skills" / "devtu-benchmark-harness" / "scripts" / "check_memorization.py"
)
ROOTS = (
    REPO / "skills",
    REPO / "plugin" / "skills",
    REPO / "plugins" / "tooluniverse" / "skills",
)


def test_the_checker_is_where_this_test_expects_it():
    assert CHECKER.is_file(), CHECKER


@pytest.mark.parametrize("strict", [False, True], ids=["hard", "strict"])
def test_no_skill_carries_dataset_specific_content(strict):
    cmd = [sys.executable, str(CHECKER), "--all"] + (["--strict"] if strict else [])
    run = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO)
    assert run.returncode == 0, (
        "check_memorization.py reported benchmark-specific content in a skill:\n"
        + run.stdout
        + run.stderr
    )
    # Guard the guard: a checker that silently scanned nothing would pass.
    scanned = [l for l in run.stdout.splitlines() if l.startswith("Scanned ")]
    assert scanned, run.stdout
    assert int(scanned[0].split()[1]) > 900, scanned[0]


def test_the_checker_reaches_the_copies_that_ship():
    """The source tree is not what other people download. A guard that reads
    only `skills/` would have let the leak survive in both plugin copies."""
    for root in ROOTS:
        assert root.is_dir(), root
    run = subprocess.run(
        [sys.executable, str(CHECKER), "--all"],
        capture_output=True,
        text=True,
        cwd=REPO,
    )
    assert run.returncode == 0, run.stdout
    # It prints nothing per-file when clean, so assert on reach instead: the
    # count has to exceed what `skills/` alone contains.
    only_source = sum(
        1
        for skill in sorted((REPO / "skills").glob("tooluniverse-*"))
        for p in list(skill.rglob("*.md")) + list(skill.glob("scripts/*.py"))
        if "references/" in str(p)
        or p.name in ("SKILL.md", "QUICK_START.md")
        or p.suffix == ".py"
    )
    scanned = int(
        [l for l in run.stdout.splitlines() if l.startswith("Scanned ")][0].split()[1]
    )
    assert scanned > only_source, (
        f"the checker scanned {scanned} files, no more than the {only_source} "
        "in skills/ alone, so the shipped copies are going unchecked"
    )


def test_a_planted_worked_solution_is_caught(tmp_path):
    """The detector has to catch the shape of the leak, not just its name. The
    section removed in #844 never said "BixBench" or "bix-54" -- it identified
    its capsule by reading that capsule's own export file."""
    planted = tmp_path / "references" / "planted.md"
    planted.parent.mkdir(parents=True)
    planted.write_text(
        '## Complete Example\n\n```python\ndf = pd.read_csv("Swarm_2.csv")\n```\n'
    )
    run = subprocess.run(
        [sys.executable, str(CHECKER), str(planted)],
        capture_output=True,
        text=True,
        cwd=REPO,
    )
    assert run.returncode != 0, (
        "a reference doc reading one dataset's export file was not flagged:\n"
        + run.stdout
    )
    # An exit code alone is not evidence: this test first passed because the
    # checker raised on a path outside the repo and exited 1 with no finding.
    assert "HARD FAILURES (1)" in run.stdout, run.stdout + run.stderr
    assert "Swarm_2.csv" in run.stdout, run.stdout
    assert "dataset-specific export filename" in run.stdout, run.stdout
    assert "Traceback" not in run.stderr, run.stderr
