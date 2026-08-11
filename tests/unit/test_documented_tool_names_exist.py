"""Guards against docs and examples naming tools that do not exist.

Companion to ``test_compose_tool_dependencies``, which pins the same class of
defect one layer down: that module checks tool names a *config* declares as a
dependency, this one checks tool names a *human-facing runnable example* tells
a user to call. The failure is identical in kind -- a name that resolves to
nothing -- but the config sweep cannot see it, because docs and examples are not
configs.

Defect this covers
------------------
``BioRxiv_search_preprints`` and ``MedRxiv_search_preprints`` were removed
because the bioRxiv/medRxiv APIs have no keyword-search endpoint at all (see
``docs/dev_docs/SEARCHING_BIORXIV.md``). The tool configs were cleaned up, but
eight ``tu.run(...)`` examples across the literature-search tutorial kept
telling users to call them, and two files under ``examples/`` still did::

    $ python -m tooluniverse.cli run BioRxiv_search_preprints \\
        '{"query":"burn resuscitation","max_results":2}'
    Error: Tool 'BioRxiv_search_preprints' not found even after loading tools
      Did you mean: BioRxiv_get_preprint, BioRxiv_list_recent_preprints, ...

    $ python -c "from tooluniverse.tools import BioRxiv_search_preprints"
    ImportError: cannot import name 'BioRxiv_search_preprints' from
    'tooluniverse.tools'

The second one is not a stale doc, it is a shipped example that cannot be
imported at all.

Scope
-----
Hand-written sources only. ``docs/tools/``, ``docs/locale/`` and
``src/tooluniverse/tools/`` are generated artifacts -- a stale name there means
the generator has not been re-run, which is a build step, not a content defect,
and hand-editing them would be reverted on the next generation.
"""

import ast
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "src" / "tooluniverse" / "data"

# Hand-written trees only; see the module docstring on generated artifacts.
SEARCH_ROOTS = (ROOT / "docs" / "guide", ROOT / "examples")

# `tu.run({"name": "X"` / `"name": "X"` inside a runnable snippet, and
# `from tooluniverse.tools import (X, Y)`.
_NAME_KEY = re.compile(r"""["']name["']\s*:\s*["']([A-Za-z_][A-Za-z0-9_]*)["']""")


def _declared_tool_names():
    """Every tool name declared in any config, mirroring the compose sweep."""
    names = set()
    for path in sorted(DATA_DIR.rglob("*.json")):
        try:
            content = json.loads(path.read_text())
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not isinstance(content, list):
            continue
        for item in content:
            if isinstance(item, dict) and isinstance(item.get("name"), str):
                names.add(item["name"])
    return names


DECLARED = _declared_tool_names()


def _tools_package_exports():
    """Names importable from ``tooluniverse.tools``, read without importing it.

    Parsed from the package's ``__all__`` so the sweep stays offline and does
    not pay the import cost of the whole tool registry.
    """
    init = ROOT / "src" / "tooluniverse" / "tools" / "__init__.py"
    tree = ast.parse(init.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets
        ):
            return {
                elt.value
                for elt in node.value.elts
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
            }
    return set()


EXPORTS = _tools_package_exports()


def _collect_name_key_references():
    """(file, tool_name) for every `"name": "X"` in a hand-written source."""
    refs = []
    for root in SEARCH_ROOTS:
        for path in sorted(root.rglob("*")):
            if path.suffix not in {".rst", ".md", ".py"} or not path.is_file():
                continue
            try:
                text = path.read_text()
            except UnicodeDecodeError:
                continue
            for match in _NAME_KEY.finditer(text):
                refs.append((str(path.relative_to(ROOT)), match.group(1)))
    return refs


def _collect_tools_imports():
    """(file, imported_name) for every `from tooluniverse.tools import ...`."""
    refs = []
    for root in SEARCH_ROOTS:
        for path in sorted(root.rglob("*.py")):
            try:
                text = path.read_text()
            except UnicodeDecodeError:
                continue
            # Only 9 of the ~190 example scripts import from the tools package;
            # parsing the rest costs 125ms of collection time for nothing.
            if "tooluniverse.tools" not in text:
                continue
            try:
                tree = ast.parse(text)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.ImportFrom)
                    and node.module == "tooluniverse.tools"
                ):
                    for alias in node.names:
                        if alias.name != "*":
                            refs.append((str(path.relative_to(ROOT)), alias.name))
    return refs


NAME_REFS = _collect_name_key_references()
IMPORT_REFS = _collect_tools_imports()


def test_sweep_found_sources_to_check():
    """Positive control: the sweeps below are vacuous if nothing was collected."""
    assert len(DECLARED) > 1000, f"only {len(DECLARED)} tool names found in {DATA_DIR}"
    assert EXPORTS, "tooluniverse.tools exports no names -- __all__ parse failed"
    assert NAME_REFS, f"no '\"name\": ...' references found under {SEARCH_ROOTS}"
    assert IMPORT_REFS, "no 'from tooluniverse.tools import' found in examples"


def test_documented_tool_names_resolve():
    """A `"name": "X"` in a runnable example must name a real tool.

    Only names that look like tool references are checked: a name that matches
    no tool AND is not capitalised like one is far more likely to be an
    unrelated `"name"` key in some sample payload, so it is skipped rather than
    guessed at.

    The capitalisation rule is deliberately conservative and does not yet cover
    lower-case tool families (`drugbank_*`, `openalex_*`), so a stale reference
    like `drugbank_get_safety` still passes. Widening it by requiring the
    name's prefix to be a real family instead --
    ``{n.split("_", 1)[0] for n in DECLARED if "_" in n}`` -- subsumes this rule
    and catches those too; it is left for a follow-up because it flags further
    pre-existing stale references beyond the ones fixed here.
    """
    unknown = sorted(
        {
            (path, name)
            for path, name in NAME_REFS
            if name not in DECLARED and re.match(r"^[A-Z][A-Za-z0-9]*_[a-z]", name)
        }
    )
    assert not unknown, (
        "docs/examples call tools that are not declared in any config: "
        f"{unknown}. A reader who copies the snippet gets "
        "\"Tool 'X' not found even after loading tools\"."
    )


def test_example_imports_from_tools_package_resolve():
    """`from tooluniverse.tools import X` in an example must actually import."""
    unknown = sorted(
        {(path, name) for path, name in IMPORT_REFS if name not in EXPORTS}
    )
    assert not unknown, (
        f"examples import names that tooluniverse.tools does not export: "
        f"{unknown}. These raise ImportError at module load, so the example "
        "cannot run at all."
    )
