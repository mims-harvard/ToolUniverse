#!/usr/bin/env python3
"""
Registry integrity test — prevents ghost tool references.

Collects every tool name *defined* in data/*.json and every tool name
*referenced* in configs, skills, and rules, then asserts that every
reference points to a real tool.

Also verifies that every JSON config ``type`` field maps to a known
Python class in the lazy registry.
"""

import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent.parent
SRC = REPO / "src" / "tooluniverse"
DATA_DIR = SRC / "data"
SKILLS_DIR = REPO / "skills"
RULES_DIR = REPO / "claude" / "rules"

sys.path.insert(0, str(REPO / "src"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_defined_tool_names() -> set[str]:
    """All tool names from ``name`` fields in data/*.json."""
    names: set[str] = set()
    for jf in DATA_DIR.glob("*.json"):
        try:
            data = json.loads(jf.read_text())
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        items = (
            data if isinstance(data, list) else [data] if isinstance(data, dict) else []
        )
        for item in items:
            if isinstance(item, dict) and "name" in item:
                names.add(item["name"])
    return names


def _load_type_names() -> set[str]:
    """All ``type`` fields from data/*.json (Python class names)."""
    types: set[str] = set()
    for jf in DATA_DIR.glob("*.json"):
        try:
            data = json.loads(jf.read_text())
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        items = (
            data if isinstance(data, list) else [data] if isinstance(data, dict) else []
        )
        for item in items:
            if isinstance(item, dict) and "type" in item:
                types.add(item["type"])
    return types


def _load_lazy_registry_class_names() -> set[str]:
    """All class names known to the static lazy registry."""
    from tooluniverse._lazy_registry_static import STATIC_LAZY_REGISTRY

    return set(STATIC_LAZY_REGISTRY.keys())


def _load_required_tools_refs() -> dict[str, list[str]]:
    """Collect tool names from ``required_tools`` arrays in data/*.json.

    Returns {source_file: [tool_name, ...]} for traceability.
    """
    refs: dict[str, list[str]] = {}
    for jf in DATA_DIR.glob("*.json"):
        try:
            data = json.loads(jf.read_text())
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        items = (
            data if isinstance(data, list) else [data] if isinstance(data, dict) else []
        )
        for item in items:
            if not isinstance(item, dict):
                continue
            for name in item.get("required_tools", []):
                if isinstance(name, str):
                    refs.setdefault(str(jf.relative_to(REPO)), []).append(name)
    return refs


# Pattern: backtick-wrapped tool names like `PubMed_search_articles`
# Requires: CamelCase prefix, underscore, then lowercase action — excludes
# ALL_CAPS env vars (TOOLUNIVERSE_*) and ontology IDs (EFO_0000537).
_TOOL_NAME_RE = re.compile(r"`((?:[A-Z][a-z][a-zA-Z0-9]*_)+[a-z][a-z_A-Z0-9]*)`")

# Known false positives: strings that match the regex but aren't tool names
_FALSE_POSITIVES = {
    "ThreadPoolExecutor",
    "CodeAgent",
    "AzureOpenAIModel",
    "SentenceTransformer",
}


def _load_markdown_tool_refs(directory: Path) -> dict[str, list[str]]:
    """Scan .md files for tool-name-like references.

    Returns {source_file: [tool_name, ...]} for traceability.
    """
    refs: dict[str, list[str]] = {}
    if not directory.exists():
        return refs
    for md in directory.rglob("*.md"):
        text = md.read_text(errors="replace")
        for match in _TOOL_NAME_RE.finditer(text):
            name = match.group(1)
            if name not in _FALSE_POSITIVES:
                refs.setdefault(str(md.relative_to(REPO)), []).append(name)
    return refs


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRegistryIntegrity:
    """Every referenced tool name must exist in the JSON-defined tool set."""

    @pytest.fixture(scope="class")
    def defined_names(self) -> set[str]:
        return _load_defined_tool_names()

    def test_defined_names_is_nonempty(self, defined_names):
        assert len(defined_names) > 100, (
            f"Expected 100+ tools, got {len(defined_names)}"
        )

    def test_required_tools_refs_exist(self, defined_names):
        """Every name in a required_tools array must be a real tool."""
        refs = _load_required_tools_refs()
        missing: list[str] = []
        for source, names in refs.items():
            for name in names:
                if name not in defined_names:
                    missing.append(f"  {name}  (referenced in {source})")
        assert not missing, "Ghost tools in required_tools arrays:\n" + "\n".join(
            sorted(set(missing))
        )

    def test_rules_refs_exist(self, defined_names):
        """Every tool-name-like reference in claude/rules/*.md must be a real tool."""
        refs = _load_markdown_tool_refs(RULES_DIR)
        missing: list[str] = []
        for source, names in refs.items():
            for name in names:
                if name not in defined_names:
                    missing.append(f"  {name}  (referenced in {source})")
        assert not missing, "Ghost tools in claude/rules/:\n" + "\n".join(
            sorted(set(missing))
        )

    def test_json_type_fields_exist_in_lazy_registry(self):
        """Every ``type`` in data/*.json must map to a known Python class."""
        types = _load_type_names()
        registry = _load_lazy_registry_class_names()
        # Also include built-in types that aren't in lazy registry
        # (e.g. BaseRESTTool is a base class used directly in some configs)
        from tooluniverse.tool_registry import _tool_registry

        all_known = registry | set(_tool_registry.keys())
        missing = types - all_known
        # Filter out types that are resolved outside the lazy registry
        # (e.g. base classes used directly, or special plugin types).
        special = {
            "BaseRESTTool",
            "VisualizationTool",
            "ClaudeCodeSkill",
            "SpecialTool",
        }
        missing -= special
        assert not missing, (
            "JSON configs reference unknown Python classes:\n"
            + "\n".join(f"  {t}" for t in sorted(missing))
        )
