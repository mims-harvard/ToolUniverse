"""Introspection for ToolUniverse optional dependency groups ("extras").

A tool being *loaded* is not the same as a tool being *runnable*.  Tool configs
are registered from JSON at load time, so ``tu status`` and
``tooluniverse-doctor`` happily count tools whose implementation needs an
optional dependency that is not installed.  Those tools only fail later, when
the user actually runs them.

This module reports which optional dependency groups declared in
``pyproject.toml`` are importable in the current environment, so the CLI can
distinguish "config-loaded" from "runtime-ready".

Keys are *import* names (what ``import x`` needs); values are the PyPI
distribution names shown to users.  The mapping is kept in sync with
``[project.optional-dependencies]`` by ``tests/unit/test_extras.py``.
"""

from __future__ import annotations

import importlib.util
import re
from collections.abc import Iterable
from pathlib import Path

# Optional dependency groups that gate *tool runtime*.  Packaging-only extras
# (dev, docs, build) and the aggregate ``all`` extra are intentionally absent —
# missing them says nothing about whether a tool can run.
EXTRA_PACKAGES: dict[str, dict[str, str]] = {
    "pdf": {
        "pymupdf": "pymupdf",
    },
    "ml": {
        "admet_ai": "admet-ai",
        "sentence_transformers": "sentence-transformers",
        "faiss": "faiss-cpu",
        "huggingface_hub": "huggingface_hub",
    },
    "embedding": {
        "sentence_transformers": "sentence-transformers",
        "faiss": "faiss-cpu",
        "huggingface_hub": "huggingface_hub",
    },
    "visualization": {
        "py3Dmol": "py3Dmol",
        "rdkit": "rdkit",
        "plotly": "plotly",
        "kaleido": "kaleido",
        "scipy": "scipy",
        "matplotlib": "matplotlib",
        "networkx": "networkx",
    },
    "graph": {
        "flask": "flask",
        "matplotlib": "matplotlib",
        "plotly": "plotly",
        "scipy": "scipy",
        "pydot": "pydot",
        "pygraphviz": "pygraphviz",
        "jinja2": "jinja2",
        "werkzeug": "werkzeug",
    },
    "bioinformatics": {
        "Bio": "biopython",
        "freesasa": "freesasa",
    },
    "singlecell": {
        "cellxgene_census": "cellxgene-census",
        "tiledbsoma": "tiledbsoma",
    },
    "smolagents": {
        "smolagents": "smolagents",
        "gradio": "gradio",
    },
}

# Extras NOT covered by ``tooluniverse[all]`` — worth telling users about,
# because "all" reads like it means all.
EXTRAS_NOT_IN_ALL = ("pdf", "singlecell", "smolagents", "client", "build")


def _is_importable(import_name: str) -> bool:
    """Return True if *import_name* can be located without importing it."""
    try:
        return importlib.util.find_spec(import_name) is not None
    except (ImportError, ValueError, AttributeError):
        # A partially-installed or shadowed package can raise here; treat it
        # as unavailable rather than crashing the health check.
        return False


def missing_packages() -> dict[str, str]:
    """Map every missing import name to its PyPI distribution name."""
    missing: dict[str, str] = {}
    for packages in EXTRA_PACKAGES.values():
        for import_name, pypi_name in packages.items():
            if import_name not in missing and not _is_importable(import_name):
                missing[import_name] = pypi_name
    return missing


def missing_extras() -> dict[str, list[str]]:
    """Map each incompletely-installed extra to its missing PyPI names.

    Extras whose dependencies are all importable are omitted, so an empty
    result means every runtime extra is satisfied.
    """
    absent = missing_packages()
    result: dict[str, list[str]] = {}
    for extra, packages in EXTRA_PACKAGES.items():
        gaps = sorted(
            pypi_name
            for import_name, pypi_name in packages.items()
            if import_name in absent
        )
        if gaps:
            result[extra] = gaps
    return result


def _module_source_path(module_name: str) -> Path | None:
    """Resolve a ``tooluniverse``-relative module name to its source file."""
    try:
        import tooluniverse

        root = Path(tooluniverse.__file__).parent
    except (ImportError, AttributeError, TypeError):
        return None
    candidate = root / (module_name.replace(".", "/") + ".py")
    return candidate if candidate.is_file() else None


def tools_needing_missing_packages(
    tool_configs: Iterable[dict],
    absent: dict[str, str] | None = None,
) -> dict[str, int]:
    """Count loaded tools whose implementation module imports a missing package.

    Returns a mapping of extra name to the number of affected tools.  This is
    an **upper bound**: a handful of tools import an optional package only as
    an enhancement and still work without it (for example the DNA tools fall
    back to a built-in restriction-enzyme table when Biopython is absent).
    Callers should present the number as "may not run", never as a failure
    count.

    Returns an empty mapping when nothing is missing, so the (cheap) source
    scan is skipped entirely on a fully-installed environment.
    """
    if absent is None:
        absent = missing_packages()
    if not absent:
        return {}

    from .tool_registry import _lazy_registry

    pattern = re.compile(
        r"^\s*(?:import|from)\s+(" + "|".join(map(re.escape, absent)) + r")\b",
        re.MULTILINE,
    )

    scanned: dict[str, frozenset] = {}

    def packages_used(module_name: str) -> frozenset:
        if module_name not in scanned:
            path = _module_source_path(module_name)
            found: frozenset = frozenset()
            if path is not None:
                try:
                    found = frozenset(pattern.findall(path.read_text(encoding="utf-8")))
                except (OSError, UnicodeDecodeError):
                    found = frozenset()
            scanned[module_name] = found
        return scanned[module_name]

    counts: dict[str, int] = {}
    for config in tool_configs:
        module_name = _lazy_registry.get(config.get("type"))
        if not module_name:
            continue
        for import_name in packages_used(module_name):
            for extra, packages in EXTRA_PACKAGES.items():
                if import_name in packages:
                    counts[extra] = counts.get(extra, 0) + 1
    return counts


def runtime_readiness(tool_configs: Iterable[dict] | None = None) -> dict:
    """Summarize whether optional tool dependencies are installed.

    Args:
        tool_configs: Loaded tool config dicts. When supplied, the result
            includes per-extra counts of tools that may not run.

    Returns a dict with ``ready`` (bool), ``missing_extras`` (extra -> missing
    PyPI names), ``affected_tools`` (extra -> upper-bound tool count), and
    ``install_hints`` (pip install strings).
    """
    gaps = missing_extras()
    affected = (
        tools_needing_missing_packages(tool_configs)
        if (tool_configs is not None and gaps)
        else {}
    )
    return {
        "ready": not gaps,
        "missing_extras": gaps,
        "affected_tools": affected,
        "install_hints": [f"pip install 'tooluniverse[{extra}]'" for extra in gaps],
    }
