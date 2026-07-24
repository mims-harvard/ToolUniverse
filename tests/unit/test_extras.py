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
