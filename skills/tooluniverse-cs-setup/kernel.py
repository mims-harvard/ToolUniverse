"""Setup helper for ToolUniverse on Claude Science (auto-loaded with the skill).

Pure-Python builder: fetch the ToolUniverse repo, parse its SKILL.md
workflow tree, and stage a rebuilt `tooluniverse-research` skill on disk.
The control-plane publish step runs separately in the `repl` tool.
Run in the `tooluniverse` conda environment.
"""
import os
import re
import sys
import json
import tarfile
import shutil
import urllib.request

REPO_TARBALL = "https://codeload.github.com/mims-harvard/ToolUniverse/tar.gz/refs/heads/"
DROP_WORKFLOWS = ("tooluniverse-install-skills",
                  "tooluniverse-claude-code-plugin",
                  "tooluniverse-codex-plugin")
AUX_ORDER = ("TOOLS_REFERENCE.md", "REPORT_TEMPLATE.md", "REPORT_GUIDELINES.md",
             "CHECKLIST.md", "EXAMPLES.md")


def tu_split_frontmatter(text):
    """Return (frontmatter_dict, body) for a SKILL.md string."""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
    fm = {}
    if not m:
        return fm, text
    for line in m.group(1).splitlines():
        mm = re.match(r"^(\w[\w-]*):\s*(.*)$", line)
        if mm:
            fm[mm.group(1)] = mm.group(2).strip()
    return fm, m.group(2)


def tu_build_research_bundle(staging="./tu_staging", ref="main"):
    """Fetch ToolUniverse and stage a rebuilt tooluniverse-research skill.

    Downloads the repo tarball, parses every tooluniverse-* workflow (dropping
    plugin/installer entries), and writes a ready-to-publish file tree under
    <staging>/out : SKILL.md, kernel.py, index.json, workflows/*.md.

    Returns a manifest dict: {out_dir, n_workflows, files, dropped}.
    """
    here = os.path.dirname(sys._getframe().f_code.co_filename) or "."
    staging = os.path.abspath(staging)
    if os.path.isdir(staging):
        shutil.rmtree(staging)
    os.makedirs(staging)

    # 1. download
    tgz = os.path.join(staging, "repo.tar.gz")
    urllib.request.urlretrieve(REPO_TARBALL + ref, tgz)

    # 2. extract only skills/**/*.md (avoids protected .mcp.json members)
    ex = os.path.join(staging, "extract")
    os.makedirs(ex)
    with tarfile.open(tgz) as tf:
        members = [m for m in tf.getmembers()
                   if "/skills/" in m.name and m.name.endswith(".md")]
        tf.extractall(ex, members=members)
    roots = [d for d in os.listdir(ex) if d.startswith("ToolUniverse")]
    if not roots:
        raise RuntimeError("skills tree not found in tarball")
    skills_dir = os.path.join(ex, roots[0], "skills")

    # 3. parse workflows
    out = os.path.join(staging, "out")
    os.makedirs(os.path.join(out, "workflows"))
    index = []
    dropped = []
    for sd in sorted(os.listdir(skills_dir)):
        if not sd.startswith("tooluniverse-"):
            continue
        smd = os.path.join(skills_dir, sd, "SKILL.md")
        if not os.path.isfile(smd):
            continue
        fm, body = tu_split_frontmatter(
            open(smd, encoding="utf-8", errors="replace").read())
        name = fm.get("name", sd)
        if name in DROP_WORKFLOWS:
            dropped.append(name)
            continue
        parts = [body.strip()]
        for aux in AUX_ORDER:
            ap = os.path.join(skills_dir, sd, aux)
            if os.path.isfile(ap):
                parts.append("\n\n---\n\n# Appendix: " + aux + "\n\n"
                             + open(ap, encoding="utf-8", errors="replace").read().strip())
        open(os.path.join(out, "workflows", name + ".md"), "w",
             encoding="utf-8").write("\n".join(parts))
        index.append({"name": name, "description": fm.get("description", "")})

    # 4. index + templated router / research-kernel
    json.dump(index, open(os.path.join(out, "index.json"), "w",
                          encoding="utf-8"), ensure_ascii=False, indent=0)
    tdir = os.path.join(here, "templates")
    router = open(os.path.join(tdir, "router_SKILL.md"), encoding="utf-8").read()
    n = str(len(index))
    # normalize any "<digits> ... workflows" count to the real number
    router = re.sub(r"\b\d+(?=(?:\s+\w+){0,2}\s+workflows\b)", n, router)
    open(os.path.join(out, "SKILL.md"), "w", encoding="utf-8").write(router)
    shutil.copy(os.path.join(tdir, "research_kernel.py"),
                os.path.join(out, "kernel.py"))

    files = []
    for r, _d, fs in os.walk(out):
        for f in fs:
            files.append(os.path.relpath(os.path.join(r, f), out))
    return {"out_dir": out, "n_workflows": len(index),
            "n_files": len(files), "dropped": dropped,
            "files_head": sorted(files)[:6]}
