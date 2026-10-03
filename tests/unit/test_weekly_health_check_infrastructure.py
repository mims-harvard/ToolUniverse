"""The weekly canary could not report, for three separate reasons.

Every run from August to October 2026 ended `failure` and
`.github/tool-health-history.jsonl` was never written once. None of that was
about tool health:

1. The commit step guarded on `git diff`, which ignores untracked files. The
   history file starts untracked, so the guard said "no history change" about a
   file the summarizer had just written, exited 0, and never staged it -- so it
   never became tracked and the next run repeated it.
2. An evicted runner kills the job rather than the step (exit 143), and one
   failed matrix leg fails the workflow. `continue-on-error` on the sweep step
   could not prevent that.
3. The expected category total is summed from the shard logs that exist, so a
   shard killed before uploading is missing from the denominator as well as the
   numerator. Run 36387615324 reported "555 of 600 -- 45 never reached" when
   shard 1 was lost whole and the true unknown was nearer 130.
"""

import importlib.util
import subprocess
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "weekly-tool-healthcheck.yml"
HISTORY = ".github/tool-health-history.jsonl"


def _workflow():
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _summarizer():
    spec = importlib.util.spec_from_file_location(
        "summarize_health_sweep", ROOT / "scripts" / "summarize_health_sweep.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _commit_step():
    steps = _workflow()["jobs"]["summarize"]["steps"]
    for step in steps:
        if "git commit" in (step.get("run") or ""):
            return step
    raise AssertionError("the summarize job no longer commits the history row")


def test_the_history_guard_stages_before_it_compares():
    """`git diff` cannot see an untracked file, and this one starts untracked."""
    run = _commit_step()["run"]
    add_at = run.index("git add")
    assert "--cached" in run, (
        "compare the index, not the worktree: a plain `git diff` reports no "
        "change for an untracked file and the row is silently dropped"
    )
    assert add_at < run.index("--cached"), (
        "the file has to be staged before the comparison, or the first run "
        "still sees nothing"
    )


def test_a_lost_shard_does_not_fail_the_workflow():
    """The header calls this a canary, not a gate; the jobs have to agree."""
    jobs = _workflow()["jobs"]

    assert jobs["sweep"].get("continue-on-error") is True, (
        "an evicted runner fails the job, not the step, and one failed matrix "
        "leg fails the whole run -- which is why every run since August was red"
    )
    assert jobs["summarize"].get("if") == "always()"
    assert jobs["summarize"].get("continue-on-error") is not True, (
        "summarize is the real gate: it must still be able to fail the run"
    )


def test_the_shard_count_reaches_the_summarizer():
    """Without it, a shard that uploaded nothing cannot be counted."""
    steps = _workflow()["jobs"]["summarize"]["steps"]
    summarize = next(
        s for s in steps if "summarize_health_sweep.py" in (s.get("run") or "")
    )

    assert "--shard-count" in summarize["run"]
    assert "SHARD_COUNT" in summarize["run"]
    assert _workflow()["env"]["SHARD_COUNT"], "SHARD_COUNT must be set to expand"


def test_a_shard_that_uploaded_nothing_is_reported(tmp_path):
    """Two of three shards reporting must not read as a complete run."""
    mod = _summarizer()
    for shard in (0, 1):
        (tmp_path / f"sweep_output_{shard}.log").write_text(
            f"[1/2] alpha{shard}: PASSED: 1 test(s)\n"
            f"[2/2] beta{shard}: PASSED: 1 test(s)\n"
        )

    results, counts, timed_out, expected, shards_seen = mod.parse_logs(
        [str(tmp_path / "*.log")]
    )
    assert shards_seen == 2

    text, row = mod.build_summary(
        results, counts, timed_out, set(), expected,
        shards_seen=shards_seen, shards_expected=3,
    )

    assert "**2** of 3" in text
    assert "1 uploaded nothing" in text
    assert "higher than the figure on the first line" in text, (
        "the category arithmetic understates the loss and the summary must say so"
    )
    assert row["shards_reported"] == 2
    assert row["shards_expected"] == 3


def test_a_complete_run_says_nothing_about_lost_shards(tmp_path):
    """The warning has to stay quiet when every shard reported."""
    mod = _summarizer()
    for shard in (0, 1, 2):
        (tmp_path / f"sweep_output_{shard}.log").write_text(
            f"[1/1] only{shard}: PASSED: 1 test(s)\n"
        )

    results, counts, timed_out, expected, shards_seen = mod.parse_logs(
        [str(tmp_path / "*.log")]
    )
    text, row = mod.build_summary(
        results, counts, timed_out, set(), expected,
        shards_seen=shards_seen, shards_expected=3,
    )

    assert "uploaded nothing" not in text
    assert "**3** of 3" in text
    assert row["shards_reported"] == row["shards_expected"] == 3


def test_the_guard_logic_behaves_on_a_real_repository(tmp_path):
    """The whole bug was git semantics, so exercise git rather than the string."""
    def git(*args):
        return subprocess.run(
            ["git", *args], cwd=tmp_path, capture_output=True, text=True
        )

    git("init", "-q", ".")
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "t")
    (tmp_path / "README").write_text("base\n")
    git("add", "README")
    git("commit", "-qm", "base")

    history = tmp_path / HISTORY
    history.parent.mkdir(parents=True, exist_ok=True)
    history.write_text('{"run": 1}\n')

    # The old guard: a plain diff sees nothing, so the row would be dropped.
    assert git("diff", "--quiet", "--", HISTORY).returncode == 0, (
        "if this ever becomes non-zero, git started reporting untracked files "
        "in `git diff` and the original guard would have worked"
    )

    # The new guard: stage first, then the index shows the addition.
    git("add", HISTORY)
    assert git("diff", "--cached", "--quiet", "--", HISTORY).returncode != 0

    git("commit", "-qm", "row 1")
    history.write_text('{"run": 1}\n{"run": 2}\n')
    git("add", HISTORY)
    assert git("diff", "--cached", "--quiet", "--", HISTORY).returncode != 0

    git("commit", "-qm", "row 2")
    git("add", HISTORY)
    assert git("diff", "--cached", "--quiet", "--", HISTORY).returncode == 0, (
        "an unchanged history must not produce an empty commit every week"
    )
