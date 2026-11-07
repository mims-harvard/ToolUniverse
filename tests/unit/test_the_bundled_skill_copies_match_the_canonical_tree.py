"""The two shipped skill trees are copies, and nothing checked they were current.

`skills/` is the canonical tree. Two packagings ship filtered copies of it:

    plugin/skills/                  the Claude Code plugin
    plugins/tooluniverse/skills/    the Codex plugin

Both are built by scripts (`plugin/sync-skills.sh`, which delegates the Codex
side to `scripts/sync-codex-plugin-skills.sh`), both are tracked in git, and
until this file nothing compared either against `skills/`. Editing a skill and
forgetting to re-run the sync shipped the old bytes to users while the review
looked at the new ones -- and that has happened: a sweep once found 7 of 8
copies drifted.

Two different checks, because the two copies are not the same kind of copy.
Measured here: of 615 files in the Claude copy, 615 are byte-identical to the
canonical tree. Of the Codex copy's 615, 452 are identical and 163 differ --
exactly one per skill, each of them `SKILL.md`, which the Codex sync rewrites
to satisfy that host's frontmatter limits. So the Claude copy is compared
directly, and the Codex copy is compared against a fresh run of its own sync.

Both compare what git tracks, not what is on disk. The first version of this
walked the directories and was red in the full suite while green on its own:
`test_peptide_deorphanization_scripts.py` executes scripts inside
`plugin/skills/.../scripts/`, Python leaves `__pycache__/*.pyc` beside them,
and those were reported as files "in the copy but not in skills/". The syncs
exclude `__pycache__/` and `*.pyc`, so none is ever committed -- and what is
committed is the whole of what this guard is about.
"""

import hashlib
import os
import pathlib
import re
import subprocess
import sys

import pytest

pytestmark = pytest.mark.unit

REPO = pathlib.Path(__file__).resolve().parents[2]
CANONICAL = REPO / "skills"
CLAUDE_COPY = REPO / "plugin" / "skills"
CODEX_COPY = REPO / "plugins" / "tooluniverse" / "skills"
CLAUDE_SYNC = REPO / "plugin" / "sync-skills.sh"
CODEX_SYNC = REPO / "scripts" / "sync-codex-plugin-skills.sh"

RESYNC = "re-run `bash plugin/sync-skills.sh` and commit the result"


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _claude_excluded():
    """The skills the Claude sync deliberately leaves out, read from the script.

    Parsed rather than restated: a list written here would be a second source
    of truth, and the failure it would cause -- a skill correctly absent from
    the copy reported as missing -- is the kind that gets the test deleted.
    """
    match = re.search(
        r'^CLAUDE_EXCLUDE="([^"]*)"', CLAUDE_SYNC.read_text(), flags=re.MULTILINE
    )
    assert match, f"{CLAUDE_SYNC} no longer declares CLAUDE_EXCLUDE"
    return set(match.group(1).split())


def _eligible_skills():
    """Canonical skills a packaging copies: the router, its family, and setup."""
    names = set()
    for path in CANONICAL.iterdir():
        if not (path / "SKILL.md").is_file():
            continue
        if path.name == "tooluniverse" or path.name.startswith("tooluniverse-"):
            names.add(path.name)
        elif path.name == "setup-tooluniverse":
            names.add(path.name)
    return names


def _tracked_under(root):
    """Repo-relative-to-`root` paths of the files git tracks beneath it.

    `git ls-files` rather than a directory walk: the trees hold build artifacts
    at test time that no sync ever copies and git never stores.
    """
    listing = subprocess.run(
        ["git", "ls-files", "-z", "--", str(root.relative_to(REPO))],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    )
    prefix = root.relative_to(REPO)
    return sorted(
        pathlib.PurePosixPath(entry).relative_to(prefix)
        for entry in listing.stdout.split("\0")
        if entry
    )


def _skill_names(paths):
    """The skill directory names a set of relative paths covers."""
    return {p.parts[0] for p in paths if len(p.parts) > 1 and p.name == "SKILL.md"}


def _files_in(root):
    return sorted(
        pathlib.PurePosixPath(p.relative_to(root).as_posix())
        for p in root.rglob("*")
        if p.is_file()
    )


def test_the_claude_copy_is_byte_identical_to_the_canonical_tree():
    """It is an unmodified filtered copy, so any difference is staleness."""
    stale = []
    for rel in _tracked_under(CLAUDE_COPY):
        source = CANONICAL / rel
        if not source.is_file():
            stale.append(f"{rel} is in the copy but not in skills/")
        elif _digest(CLAUDE_COPY / rel) != _digest(source):
            stale.append(f"{rel} differs from skills/{rel}")

    assert not stale, (
        f"{len(stale)} file(s) in plugin/skills/ do not match skills/; {RESYNC}\n  "
        + "\n  ".join(stale[:20])
    )


def test_every_skill_the_claude_packaging_ships_is_present():
    """A newly added skill that was never synced is missing, not merely stale."""
    expected = _eligible_skills() - _claude_excluded()
    present = _skill_names(_tracked_under(CLAUDE_COPY))

    assert expected - present == set(), (
        f"skills missing from plugin/skills/: {sorted(expected - present)}; {RESYNC}"
    )
    assert present - expected == set(), (
        "plugin/skills/ ships skills the canonical tree does not have or excludes: "
        f"{sorted(present - expected)}"
    )


@pytest.fixture(scope="module")
def fresh_codex_tree(tmp_path_factory):
    """One rebuild of the Codex copy, shared by the two tests that read it.

    Module-scoped because the sync takes ~35 s against `pytest.ini`'s 60 s
    timeout: running it per test spent the budget twice and the second one blew
    it on a loaded machine. The tests below stay separate because they answer
    different questions, and the timeout mark covers the test that pays for the
    fixture.

    `scripts/sync-codex-plugin-skills.sh` takes `CODEX_PLUGIN_SKILLS_DEST` for
    exactly this -- building somewhere else so a test never regenerates tracked
    files in place. The interpreter is pinned to this one because the sync's
    description step needs PyYAML, and a `python3` on PATH without it once
    rewrote real descriptions down to a bare `">-"`.
    """
    fresh = tmp_path_factory.mktemp("codex") / "skills"
    env = dict(os.environ)
    env["CODEX_PLUGIN_SKILLS_DEST"] = str(fresh)
    env["CODEX_PLUGIN_PYTHON"] = sys.executable

    result = subprocess.run(
        [str(CODEX_SYNC)], cwd=REPO, env=env, capture_output=True, text=True
    )
    assert result.returncode == 0, f"the Codex sync failed:\n{result.stderr[-2000:]}"
    return fresh


@pytest.mark.timeout(300)
def test_the_codex_copy_matches_a_fresh_run_of_its_own_sync(fresh_codex_tree):
    """The Codex copy rewrites each SKILL.md, so it is compared to a rebuild."""
    fresh = fresh_codex_tree

    tracked_files, fresh_files = _tracked_under(CODEX_COPY), _files_in(fresh)
    assert tracked_files == fresh_files, (
        "plugins/tooluniverse/skills/ holds a different set of files than its "
        f"sync produces; {RESYNC}\n"
        f"  only tracked: {sorted(set(tracked_files) - set(fresh_files))[:10]}\n"
        f"  only fresh:   {sorted(set(fresh_files) - set(tracked_files))[:10]}"
    )

    stale = [
        str(rel)
        for rel in tracked_files
        if _digest(CODEX_COPY / rel) != _digest(fresh / rel)
    ]
    assert not stale, (
        f"{len(stale)} file(s) in plugins/tooluniverse/skills/ are not what the "
        f"sync produces; {RESYNC}\n  " + "\n  ".join(stale[:20])
    )


@pytest.mark.timeout(300)
def test_the_sync_never_produces_a_file_the_repository_would_refuse(fresh_codex_tree):
    """A synced file that `.gitignore` covers can never equal what is committed.

    `.gitignore` line 159 ignores `*_SUMMARY.md`. The canonical copy of
    `setup-tooluniverse/SKILL_SUMMARY.md` predates the rule and is tracked, so
    the syncs copied it into both plugin trees -- where the rule does apply.
    The result was a file present on every machine that ran the sync and absent
    for everyone who installed a plugin from git, and a tracked copy that could
    not match its own generator no matter who ran it.

    Stated as the invariant rather than the instance: whatever the ignore rules
    grow into, output the repository will not store is output no packaging can
    ship.
    """
    fresh = fresh_codex_tree

    # check-ignore is asked about the paths as they would land in the tracked
    # tree, not about their temp-directory twins, which no rule mentions.
    candidates = [str(CODEX_COPY.relative_to(REPO) / rel) for rel in _files_in(fresh)]
    ignored = subprocess.run(
        ["git", "check-ignore", "--stdin"],
        cwd=REPO,
        input="\n".join(candidates),
        capture_output=True,
        text=True,
    )

    assert not ignored.stdout.strip(), (
        "the sync produces files .gitignore covers, so they cannot be committed "
        "and users installing from git will not get them:\n  "
        + "\n  ".join(ignored.stdout.split())
    )
