"""Tests for optional-dependency ("extras") reporting.

Covers the distinction between a tool being *config-loaded* and being
*runtime-ready*: tools backed by an uninstalled optional dependency register
fine and only fail when run, so the health check must not report an all-clear.
"""

import re
from pathlib import Path
from unittest.mock import patch

import pytest

from tooluniverse import extras
from tooluniverse.extras import (
    EXTRA_PACKAGES,
    EXTRAS_NOT_IN_ALL,
    missing_extras,
    missing_packages,
    runtime_readiness,
    tools_needing_missing_packages,
)

PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"


def _raw_pyproject_extras():
    """Return the raw {extra: [requirement strings]} table from pyproject.toml."""
    try:
        import tomllib
    except ImportError:  # Python < 3.11
        pytest.skip("tomllib unavailable")
    with open(PYPROJECT, "rb") as fh:
        data = tomllib.load(fh)
    return data["project"]["optional-dependencies"]


def _load_pyproject_extras():
    """Return {extra: [normalized pypi names]} from pyproject.toml."""
    result = {}
    for extra, requirements in _raw_pyproject_extras().items():
        names = []
        for requirement in requirements:
            # Strip version specifiers / markers / extras: "faiss-cpu==1.12.0"
            name = re.split(r"[<>=!~;\[]", requirement, maxsplit=1)[0].strip()
            names.append(name.lower().replace("_", "-"))
        result[extra] = names
    return result


def _extras_included_in_all():
    """Return the set of extras that ``tooluniverse[all]`` pulls in.

    ``all`` is declared as a self-referential requirement,
    ``tooluniverse[dev,docs,...]``, so the extra names live inside the
    brackets rather than in separate list entries.
    """
    included = set()
    for requirement in _raw_pyproject_extras()["all"]:
        match = re.search(r"\[([^\]]+)\]", requirement)
        if match:
            included.update(part.strip() for part in match.group(1).split(","))
    return included


def _normalize(name: str) -> str:
    return name.lower().replace("_", "-")


class TestExtrasMatchPyproject:
    """EXTRA_PACKAGES must stay in sync with [project.optional-dependencies]."""

    def test_every_extra_is_declared(self):
        declared = _load_pyproject_extras()
        for extra in EXTRA_PACKAGES:
            assert extra in declared, f"'{extra}' is not declared in pyproject.toml"

    def test_every_package_is_declared_in_its_extra(self):
        declared = _load_pyproject_extras()
        for extra, packages in EXTRA_PACKAGES.items():
            for pypi_name in packages.values():
                assert _normalize(pypi_name) in declared[extra], (
                    f"'{pypi_name}' is mapped to extra '{extra}' but is not "
                    f"listed under that extra in pyproject.toml"
                )

    def test_extras_not_in_all_is_accurate(self):
        """`[all]` is a misnomer; verify the documented exclusion list."""
        declared = _load_pyproject_extras()
        included = _extras_included_in_all()
        assert included, "could not parse the [all] extra"
        for extra in EXTRAS_NOT_IN_ALL:
            assert extra in declared, f"'{extra}' is not a real extra"
            assert extra not in included, (
                f"'{extra}' IS covered by [all]; remove it from EXTRAS_NOT_IN_ALL"
            )

    def test_all_covers_everything_else(self):
        """Any extra absent from [all] must be documented in EXTRAS_NOT_IN_ALL."""
        declared = _load_pyproject_extras()
        included = _extras_included_in_all()
        for extra in declared:
            if extra == "all" or extra in included:
                continue
            assert extra in EXTRAS_NOT_IN_ALL, (
                f"'{extra}' is not covered by [all] and is not listed in "
                f"EXTRAS_NOT_IN_ALL"
            )


class TestMissingDetection:
    def test_nothing_missing_when_all_importable(self):
        with patch.object(extras, "_is_importable", return_value=True):
            assert missing_packages() == {}
            assert missing_extras() == {}

    def test_all_missing_when_none_importable(self):
        with patch.object(extras, "_is_importable", return_value=False):
            gaps = missing_extras()
        assert set(gaps) == set(EXTRA_PACKAGES)
        assert "biopython" in gaps["bioinformatics"]

    def test_single_missing_package_flags_only_its_extras(self):
        def only_rdkit_missing(name):
            return name != "rdkit"

        with patch.object(extras, "_is_importable", side_effect=only_rdkit_missing):
            gaps = missing_extras()
        assert gaps == {"visualization": ["rdkit"]}

    def test_shared_package_flags_every_extra_that_needs_it(self):
        def only_matplotlib_missing(name):
            return name != "matplotlib"

        with patch.object(
            extras, "_is_importable", side_effect=only_matplotlib_missing
        ):
            gaps = missing_extras()
        assert set(gaps) == {"visualization", "graph"}

    def test_importable_check_survives_broken_package(self):
        with patch(
            "importlib.util.find_spec", side_effect=ValueError("broken __spec__")
        ):
            assert extras._is_importable("anything") is False


class TestRuntimeReadiness:
    def test_ready_when_nothing_missing(self):
        with patch.object(extras, "_is_importable", return_value=True):
            readiness = runtime_readiness([])
        assert readiness["ready"] is True
        assert readiness["missing_extras"] == {}
        assert readiness["install_hints"] == []

    def test_not_ready_when_something_missing(self):
        with patch.object(extras, "_is_importable", return_value=False):
            readiness = runtime_readiness(None)
        assert readiness["ready"] is False
        assert readiness["missing_extras"]
        assert "pip install 'tooluniverse[ml]'" in readiness["install_hints"]

    def test_affected_tools_skipped_without_configs(self):
        with patch.object(extras, "_is_importable", return_value=False):
            readiness = runtime_readiness(None)
        assert readiness["affected_tools"] == {}


class TestToolCounting:
    def test_no_scan_when_nothing_missing(self):
        configs = [{"name": "T", "type": "ADMETAITool"}]
        assert tools_needing_missing_packages(configs, absent={}) == {}

    def test_counts_tools_whose_module_imports_missing_package(self):
        configs = [
            {"name": "A", "type": "ADMETAITool"},
            {"name": "B", "type": "ADMETAITool"},
        ]
        counts = tools_needing_missing_packages(
            configs, absent={"admet_ai": "admet-ai"}
        )
        assert counts.get("ml") == 2

    def test_ignores_tools_with_unknown_type(self):
        configs = [{"name": "X", "type": "NoSuchToolTypeAnywhere"}]
        counts = tools_needing_missing_packages(
            configs, absent={"admet_ai": "admet-ai"}
        )
        assert counts == {}

    def test_ignores_tools_not_using_the_missing_package(self):
        """A plain REST tool must not be blamed on a missing ML package."""
        configs = [{"name": "R", "type": "RESTTool"}]
        counts = tools_needing_missing_packages(
            configs, absent={"admet_ai": "admet-ai"}
        )
        assert counts == {}


class TestDoctorOutput:
    """The regression this fixes: a false all-clear on a partial install."""

    def _run_doctor(self, health, importable):
        from tooluniverse import doctor

        class FakeTU:
            all_tools = [{"name": "A", "type": "ADMETAITool"}]

            def load_tools(self):
                pass

            def get_tool_health(self):
                return health

        with (
            patch("tooluniverse.ToolUniverse", return_value=FakeTU()),
            patch.object(extras, "_is_importable", side_effect=importable),
        ):
            import io
            from contextlib import redirect_stdout

            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = doctor.main()
            return code, buffer.getvalue()

    HEALTHY = {
        "total": 100,
        "available": 100,
        "unavailable": 0,
        "unavailable_list": [],
        "details": {},
    }

    def test_no_false_all_clear_when_extra_missing(self):
        code, output = self._run_doctor(
            self.HEALTHY, importable=lambda name: name != "admet_ai"
        )
        assert code == 0
        assert "optional dependency group(s) not installed" in output
        assert "pip install 'tooluniverse[ml]'" in output
        assert "All tools loaded and every optional dependency" not in output

    def test_all_clear_only_when_fully_installed(self):
        code, output = self._run_doctor(self.HEALTHY, importable=lambda name: True)
        assert code == 0
        assert "All tools loaded and every optional dependency group is installed!" in (
            output
        )
        assert "not installed" not in output

    def test_load_failures_still_reported(self):
        health = {
            "total": 100,
            "available": 99,
            "unavailable": 1,
            "unavailable_list": ["BrokenTool"],
            "details": {
                "BrokenTool": {
                    "error": "No module named 'torch'",
                    "missing_package": "torch",
                }
            },
        }
        code, output = self._run_doctor(health, importable=lambda name: True)
        assert code == 0
        assert "BrokenTool" in output
        assert "pip install torch" in output
        assert "All tools loaded and every optional dependency" not in output

    def test_reports_both_failures_and_missing_extras(self):
        health = {
            "total": 100,
            "available": 99,
            "unavailable": 1,
            "unavailable_list": ["BrokenTool"],
            "details": {"BrokenTool": {"error": "boom", "missing_package": None}},
        }
        code, output = self._run_doctor(
            health, importable=lambda name: name != "admet_ai"
        )
        assert code == 0
        assert "BrokenTool" in output
        assert "[ml]" in output

    def test_initialization_failure_returns_1(self):
        from tooluniverse import doctor

        with patch("tooluniverse.ToolUniverse", side_effect=Exception("nope")):
            assert doctor.main() == 1


# --- base dependencies vs. runtime extras -----------------------------------
#
# An extra can only gate a tool if the package it names is *not* also a base
# dependency. Four packages were declared in both places at once -- scipy and
# networkx (graph, visualization), faiss-cpu (embedding, ml) and flask (graph)
# -- so those extras could never mean anything, everyone paid for 145 MB of
# them, and ``missing_extras()`` could never report them. These two tests keep
# that from coming back.

SRC = Path(__file__).resolve().parents[2] / "src" / "tooluniverse"

# huggingface_hub is imported while ToolUniverse itself imports, so it has to be
# a base dependency; naming it in embedding/ml/space as well is redundant but
# harmless. Anything else appearing here means an extra that cannot gate.
BASE_AND_EXTRA_EXEMPT = {"huggingface-hub"}


def _base_dependency_names():
    with open(PYPROJECT, "rb") as fh:
        import tomllib

        data = tomllib.load(fh)
    return {
        re.split(r"[<>=!~;\[]", requirement, maxsplit=1)[0]
        .strip()
        .lower()
        .replace("_", "-")
        for requirement in data["project"]["dependencies"]
    }


def _runtime_extra_distributions():
    return {
        pypi_name.lower().replace("_", "-")
        for packages in EXTRA_PACKAGES.values()
        for pypi_name in packages.values()
    }


def test_no_package_is_both_a_base_dependency_and_a_runtime_extra():
    overlap = _base_dependency_names() & _runtime_extra_distributions()
    assert overlap == BASE_AND_EXTRA_EXEMPT, (
        "these packages are declared as base dependencies and inside a runtime "
        f"extra: {sorted(overlap - BASE_AND_EXTRA_EXEMPT)}. A base dependency is "
        "always installed, so the extra naming it cannot gate anything and "
        "missing_extras() can never report it. Put the package in one place."
    )


def test_extras_only_packages_are_never_imported_unguarded_at_module_level():
    """A package behind an extra may not be imported at module scope unguarded.

    A bare module-level import of an uninstalled package makes the whole tool
    module unimportable, and the failure surfaces as "Tool ... not found even
    after loading tools" with "Check tool name spelling" -- the real cause,
    ``No module named 'x'``, only reaches the log. Wrapping the import (either
    setting a HAS_* flag or re-raising with the extra named) is what turns that
    into an answer the caller can act on.
    """
    import ast

    import_to_dist = {
        "scipy": "scipy",
        "networkx": "networkx",
        "faiss": "faiss-cpu",
        "flask": "flask",
        "matplotlib": "matplotlib",
        "plotly": "plotly",
        "rdkit": "rdkit",
        "Bio": "biopython",
        "sentence_transformers": "sentence-transformers",
        "easyocr": "easyocr",
        "fitz": "pymupdf",
        "playwright": "playwright",
        "markitdown": "markitdown",
        "indigo": "epam.indigo",
        "ddgs": "ddgs",
        "sympy": "sympy",
    }
    gated = _runtime_extra_distributions() - _base_dependency_names()
    watched = {
        import_name: dist
        for import_name, dist in import_to_dist.items()
        if dist in gated
    }
    assert watched, "expected at least one extras-only package to watch"

    offenders = []
    for path in SRC.rglob("*.py"):
        # src/tooluniverse/remote/* are separate deployables: each directory
        # ships its own requirements.txt and starts its own MCP server on a
        # remote worker. They import packages this project never declares at
        # all (scanpy, for one), which is only possible because nothing here
        # imports them.
        if "remote" in path.relative_to(SRC).parts:
            continue
        try:
            tree = ast.parse(path.read_text(errors="ignore"))
        except SyntaxError:  # pragma: no cover - not our concern here
            continue
        for node in tree.body:  # module scope only; a try block is nested
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                modules = [node.module or ""]
            else:
                continue
            for module in modules:
                top = module.split(".")[0]
                if top in watched:
                    offenders.append(f"{path.relative_to(SRC)}:{node.lineno} ({top})")

    assert not offenders, (
        "these module-level imports of extras-only packages are unguarded, so "
        "the tools behind them disappear with a misleading error when the extra "
        f"is absent: {offenders}"
    )


# The guards above only take their False branch when the package is absent, and
# `[dev]` installs all three so CI never gets there on its own. Flip the flag
# instead, so the message a user would actually see is covered either way.
@pytest.mark.parametrize(
    "module_name, flag, class_name, arguments, expected_package, config",
    [
        (
            "tooluniverse.humanbase_tool",
            "HAS_NETWORKX",
            "HumanBaseTool",
            {"gene_list": ["TP53", "EGFR", "BRCA1"]},
            "networkx",
            {},
        ),
        (
            "tooluniverse.coexpression_module_tool",
            "HAS_NETWORKX",
            "CoexpressionModuleTool",
            {"expression": {"TP53": [1.0, 2.0, 3.0], "EGFR": [2.0, 1.0, 3.0]}},
            "networkx",
            {},
        ),
        (
            "tooluniverse.chem_tool",
            "HAS_INDIGO",
            "ChEMBLTool",
            {"query": "CC(=O)Oc1ccccc1C(=O)O"},
            "epam.indigo",
            {},
        ),
        (
            "tooluniverse.expression_anova_tool",
            "HAS_SCIPY",
            "ExpressionANOVAPerGeneTool",
            {
                "counts_file": "/nonexistent.csv",
                "meta_file": "/nonexistent.csv",
                "group_col": "g",
                "mode": "anova",
            },
            "scipy",
            {},
        ),
    ],
)
def test_a_tool_whose_extra_is_absent_says_what_to_install(
    monkeypatch, module_name, flag, class_name, arguments, expected_package, config
):
    """The error has to name the package and the extra, not just fail.

    Without the guard the module is unimportable, the tool never registers, and
    the caller is told "Tool ... not found even after loading tools" with
    "Check tool name spelling" while the real cause stays in the log.
    """
    import importlib

    module = importlib.import_module(module_name)
    monkeypatch.setattr(module, flag, False)
    tool = getattr(module, class_name)({"name": "t", "type": class_name, **config})

    result = tool.run(arguments)

    assert result["status"] == "error"
    assert expected_package in result["error"]
    assert "pip install" in result["error"], (
        f"the error must say how to fix it, got: {result['error']}"
    )


def test_web_search_says_what_to_install_before_spawning_ddgs(monkeypatch):
    """DDGS runs in a subprocess, so nothing imports it in this process.

    Without the check the failure arrives as "DDGS subprocess failed with exit
    code 1: ModuleNotFoundError: No module named 'ddgs'", which names the cause
    but not the cure.
    """
    import importlib.util

    from tooluniverse.web_search_tool import WebSearchTool

    real_find_spec = importlib.util.find_spec
    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name, *a, **kw: None
        if name == "ddgs"
        else real_find_spec(name, *a, **kw),
    )
    tool = WebSearchTool({"name": "web_search", "type": "WebSearchTool"})

    with pytest.raises(RuntimeError, match=r"tooluniverse\[websearch\]"):
        tool._search_with_ddgs("anything")


def test_a_guideline_extraction_without_markitdown_names_the_extra(monkeypatch):
    """The three call sites sit in `except Exception: return str(e)` handlers,
    so the helper has to carry the instruction in the exception itself."""
    from tooluniverse import unified_guideline_tools as module

    monkeypatch.setattr(module, "MARKITDOWN_AVAILABLE", False)

    with pytest.raises(RuntimeError, match=r"tooluniverse\[documents\]"):
        module._markitdown()


def test_only_the_rendering_path_of_url_tool_needs_the_browser_extra(monkeypatch):
    """get_webpage_title and plain downloads run on requests alone.

    Guarding ``run`` wholesale was wrong and a test caught it: URLHTMLTagTool
    fetches with requests and only falls back to a browser for pages requests
    cannot turn into text. The check belongs where the rendering starts.
    """
    from unittest.mock import MagicMock

    from tooluniverse import url_tool

    monkeypatch.setattr(url_tool, "HAS_PLAYWRIGHT", False)

    html_head = MagicMock()
    html_head.headers = {"Content-Type": "text/html; charset=utf-8"}
    monkeypatch.setattr(url_tool.requests, "head", lambda *a, **kw: html_head)

    tool = url_tool.URLToPDFTextTool(
        {"name": "t", "type": "URLToPDFTextTool", "fields": {"return_key": "text"}}
    )
    result = tool.run({"url": "https://example.com"})

    assert result["status"] == "error"
    assert "tooluniverse[browser]" in result["error"]


def test_a_plain_download_still_works_without_the_browser_extra(monkeypatch):
    """The non-HTML path must not be blocked by a missing browser."""
    from unittest.mock import MagicMock

    from tooluniverse import url_tool

    monkeypatch.setattr(url_tool, "HAS_PLAYWRIGHT", False)

    head = MagicMock()
    head.headers = {"Content-Type": "text/plain"}
    body = MagicMock()
    body.status_code = 200
    body.text = "plain text content"
    monkeypatch.setattr(url_tool.requests, "head", lambda *a, **kw: head)
    monkeypatch.setattr(url_tool.requests, "get", lambda *a, **kw: body)

    tool = url_tool.URLToPDFTextTool(
        {"name": "t", "type": "URLToPDFTextTool", "fields": {"return_key": "text"}}
    )
    result = tool.run({"url": "https://example.com"})

    assert "browser" not in str(result).lower()
    assert "plain text content" in str(result)
