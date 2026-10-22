"""Generate a provider README from its own manifest and setup skill.

The generator lived in a session scratchpad that is now gone, which is the
third time something load-bearing has done that. This copy is written beside
the work it serves.
"""

import pathlib
import re
import sys
import textwrap

sys.path.insert(0, "src")
from tooluniverse.remote_resident import manifest as M  # noqa: E402

TEMPLATE = (pathlib.Path(__file__).parent / "readme_template.md").read_text()


def build(slug: str, title: str) -> str:
    root = pathlib.Path("src/tooluniverse/remote") / slug
    skill_path = pathlib.Path(f"skills/setup-{slug}-remote-tool/SKILL.md")
    skill = skill_path.read_text()
    m = M.load(root / "provider.toml")

    def grab(pattern, flags=0):
        hit = re.search(pattern, skill, flags)
        if hit is None:
            raise SystemExit(f"{slug}: the skill has no {pattern!r}")
        return hit.group(1)

    status = grab(r"^> Validation status(?: \(\d{4}-\d{2}-\d{2}\))?: (.+)$", re.M)
    terms = ("incomplete", "blocked", "unmeasured", "unvalidated", "not a ", "not an ")
    if not any(t in status.lower() for t in terms):
        status = (
            status.replace("untested", "unvalidated", 1)
            if "untested" in status
            else status.rstrip().rstrip(".")
            + ". Evidence is one card and one operator, so public publication,"
            " cross-user isolation, concurrency and recovery are unvalidated."
        )

    budget = m.vram_budget_gb
    if m.gpu_policy == "required" and budget:
        line = (
            f"The measured VRAM budget is {budget} GiB; read the envelope it was"
            f" measured at in the manifest before co-tenanting anything else on"
            f" the card, because a larger request exceeds it."
        )
    else:
        line = (
            "Read the measured budget and the envelope it was measured at in"
            " the manifest before co-tenanting anything else on the card."
        )

    return TEMPLATE.format(
        title=title,
        status=status,
        operation=grab(r"^Operation: (\S+)", re.M),
        module=grab(r"^python -m (tooluniverse\.remote\.\S+)", re.M),
        endpoint="http://127.0.0.1:%s/mcp"
        % grab(r"endpoint is http://127\.0\.0\.1:(\d+)/mcp"),
        budget_line="\n  ".join(textwrap.wrap(line, 76)),
        doctor=grab(r"^(tu doctor --forward \S+ --json)$", re.M),
        relay=grab(
            r"^(tu serve --share --forward \S+ --name \S+ --workers [12])$", re.M
        ),
        share=grab(r"^(tu remote share \S+)$", re.M),
        share_options=grab(r"^(tu remote share \S+ --name \S+ --workers [12])$", re.M),
        slug=slug,
        description=m.description,
    )


if __name__ == "__main__":
    slug, title = sys.argv[1], sys.argv[2]
    out = pathlib.Path("src/tooluniverse/remote") / slug / "README.md"
    out.write_text(build(slug, title))
    print(f"{slug}: {len(out.read_text().splitlines())} lines")
