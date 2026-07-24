"""ToolUniverse research helpers (auto-loaded with the skill).

Run cells in the `tooluniverse` conda environment.
"""
import os
import sys
import json
import re

DEFAULT_CACHE = "./tooluniverse_cache"


def get_tu(cache_dir=None):
    """Return a loaded ToolUniverse instance.

    The host home (~/.tooluniverse) is not writable in this sandbox, so the
    result cache is redirected to the workspace via TOOLUNIVERSE_CACHE_DIR.
    """
    if cache_dir is None:
        cache_dir = DEFAULT_CACHE
    os.environ.setdefault("TOOLUNIVERSE_CACHE_DIR", os.path.abspath(cache_dir))
    os.makedirs(os.environ["TOOLUNIVERSE_CACHE_DIR"], exist_ok=True)
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()
    return tu


def tu_workflows():
    """List every bundled workflow: [{'name', 'description'}, ...]."""
    here = os.path.dirname(sys._getframe().f_code.co_filename) or "."
    return json.load(open(os.path.join(here, "index.json"), encoding="utf-8"))


def find_tu_workflow(query, top=5):
    """Rank bundled workflows by relevance to `query`.

    Name-token matches are weighted heavily; the score also rewards covering
    distinct query terms rather than one term repeated many times.
    """
    here = os.path.dirname(sys._getframe().f_code.co_filename) or "."
    idx = json.load(open(os.path.join(here, "index.json"), encoding="utf-8"))
    terms = sorted({t for t in re.split(r"\W+", query.lower()) if len(t) > 2})
    scored = []
    for e in idx:
        name = e["name"].replace("tooluniverse-", "").replace("-", " ").lower()
        desc = e.get("description", "").lower()
        score = 0.0
        covered = 0
        for t in terms:
            n_hits = name.count(t)
            d_hits = desc.count(t)
            if n_hits or d_hits:
                covered += 1
            score += 5.0 * n_hits + min(d_hits, 3)
        score += 2.0 * covered
        if score:
            scored.append((score, e["name"], e.get("description", "")))
    scored.sort(reverse=True)
    return [{"name": n, "description": d, "score": round(s, 1)}
            for s, n, d in scored[:top]]


def tu_workflow(name):
    """Return the full step-by-step procedure for one workflow."""
    here = os.path.dirname(sys._getframe().f_code.co_filename) or "."
    if not name.startswith("tooluniverse-"):
        name = "tooluniverse-" + name
    path = os.path.join(here, "workflows", name + ".md")
    if not os.path.isfile(path):
        raise FileNotFoundError("No such workflow: " + name)
    return open(path, encoding="utf-8").read()


def tu_tool_info(tu, name):
    """Return the JSON spec (incl. argument schema) for a tool by name."""
    for t in getattr(tu, "all_tools", []) or []:
        if t.get("name") == name:
            return t
    return None
