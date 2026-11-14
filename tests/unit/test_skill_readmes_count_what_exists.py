"""The skill READMEs must count the skills that exist, and list all of them.

Filed as #874 by an outside reader who noticed the two READMEs disagree with
each other: README.md advertised "68 pre-built research workflows" while
skills/README.md said "69 pre-built research skills". Both were stale, and the
table under skills/README.md's own "All Skills" heading listed 73 of the 229
skill directories -- 94 research skills and 62 remote-tool setup skills were
missing from a list that claims to be complete.

Two earlier rounds (#859, #860) fixed this class of stale count elsewhere and
did not touch these two files, which is the argument for a test rather than
another correction: a number maintained by hand goes stale between the commit
that fixes it and the next skill added.

The issue's own suggestion -- "230+" -- would have been wrong in the other
direction. 229 directories exist, but 63 of them install a GPU-backed model
and 2 are for developing ToolUniverse itself; calling all of them research
workflows overstates the research catalogue by half.
"""

import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_SKILLS = _ROOT / "skills"
_SKILLS_README = _SKILLS / "README.md"
_ROOT_README = _ROOT / "README.md"

_ACCESS = {
    "tooluniverse",
    "tooluniverse-antigravity-plugin",
    "tooluniverse-claude-code-plugin",
    "tooluniverse-codex-plugin",
    "tooluniverse-connect",
    "tooluniverse-cs-setup",
    "tooluniverse-custom-tool",
    "tooluniverse-database-logins",
    "tooluniverse-publish-tool",
    "tooluniverse-share-computer",
    "tooluniverse-use-shared-computer",
}


def _directories():
    return {
        d.name for d in _SKILLS.iterdir() if d.is_dir() and (d / "SKILL.md").exists()
    }


def _buckets():
    names = _directories()
    remote = {
        n for n in names if n.startswith("setup-") or n == "host-and-share-remote-tool"
    }
    access = {n for n in names if n in _ACCESS}
    research = {n for n in names if n.startswith("tooluniverse")} - access
    developer = names - remote - access - research
    return {
        "Research Skills": research,
        "Setup and Access": access,
        "Remote Tool Setup": remote,
        "Developer Skills": developer,
    }


def _sections():
    """Each '### Heading (n)' mapped to (declared n, the skill names listed under it)."""
    text = _SKILLS_README.read_text(encoding="utf-8")
    out = {}
    headings = list(re.finditer(r"^### (.+?) \((\d+)\)\s*$", text, re.M))
    for i, m in enumerate(headings):
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        body = text[m.end() : end]
        out[m.group(1)] = (
            int(m.group(2)),
            re.findall(r"^\| `([^`]+)` \|", body, re.M),
        )
    return out


def test_every_skill_directory_is_listed():
    listed = {name for _, names in _sections().values() for name in names}
    missing = sorted(_directories() - listed)
    assert not missing, (
        f"{len(missing)} skill directories are absent from a table headed "
        f'"All Skills": {missing[:8]}'
    )


def test_nothing_is_listed_that_does_not_exist():
    listed = {name for _, names in _sections().values() for name in names}
    phantom = sorted(listed - _directories())
    assert not phantom, f"listed but no such directory: {phantom}"


def test_no_skill_is_listed_twice():
    listed = [name for _, names in _sections().values() for name in names]
    duplicated = sorted({n for n in listed if listed.count(n) > 1})
    assert not duplicated, f"listed in more than one section: {duplicated}"


@pytest.mark.parametrize("heading", sorted(_buckets()))
def test_each_heading_declares_the_count_it_lists(heading):
    sections = _sections()
    assert heading in sections, f"section '{heading}' is gone from skills/README.md"
    declared, names = sections[heading]
    assert declared == len(names), (
        f"'{heading}' says ({declared}) and lists {len(names)}"
    )
    assert set(names) == _buckets()[heading], (
        f"'{heading}' does not list exactly the directories that belong to it"
    )


def test_the_skills_readme_headline_matches_its_tables():
    text = _SKILLS_README.read_text(encoding="utf-8")
    headline = text.split("\n\n")[1]
    buckets = _buckets()
    total = sum(len(v) for v in buckets.values())
    for number in (
        total,
        len(buckets["Research Skills"]),
        len(buckets["Remote Tool Setup"]),
    ):
        assert str(number) in headline, (
            f"the opening line does not carry {number}: {headline!r}"
        )


def test_the_root_readme_does_not_overstate_the_research_catalogue():
    line = next(
        line
        for line in _ROOT_README.read_text(encoding="utf-8").splitlines()
        if "Agent Skills" in line and "pre-built" in line
    )
    claimed = int(re.search(r"(\d+) pre-built", line).group(1))
    assert claimed == len(_buckets()["Research Skills"]), (
        f"README.md claims {claimed} pre-built research skills; "
        f"{len(_buckets()['Research Skills'])} exist"
    )
