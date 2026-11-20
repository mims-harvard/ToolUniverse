"""Tests for the bounded Gen repository metadata tool."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
from jsonschema import Draft202012Validator

from tooluniverse import ToolUniverse
from tooluniverse.gen_tool import GenRepositoryInspectTool


pytestmark = pytest.mark.unit

_DATA_ROOT = Path(__file__).parents[2] / "src" / "tooluniverse" / "data"
_CONFIG = json.loads((_DATA_ROOT / "gen_tools.json").read_text(encoding="utf-8"))[0]


class _FakeRepository:
    def __init__(self, path):
        self.path = path
        self._branches = [
            SimpleNamespace(
                name="main",
                is_current=True,
                head="abc123",
                dirty=False,
                remote="origin",
            ),
            SimpleNamespace(
                name="experiment",
                is_current=False,
                head="def456",
                dirty=True,
                remote=None,
            ),
        ]
        self.current_branch = self._branches[0]
        self._operations = [
            SimpleNamespace(
                id=f"operation-{index}",
                parent_id=f"operation-{index - 1}" if index else None,
                date="2026-11-20T00:00:00Z",
                is_head=index == 0,
                committer="Private Author",
                email="private@example.org",
                message="Private operation message",
            )
            for index in range(5)
        ]
        self.samples = [
            SimpleNamespace(name="reference", collection="yeast"),
            SimpleNamespace(name="sample-1", collection="yeast"),
        ]

    def get_branches(self):
        return self._branches

    def get_operations(self, branch=None, limit=None):
        self.operation_query = (branch, limit)
        return self._operations[:limit]


def _tool():
    return GenRepositoryInspectTool(dict(_CONFIG))


def _authorized_repository(monkeypatch, tmp_path):
    root = tmp_path / "repositories"
    repository_path = root / "yeast-study"
    gen_directory = repository_path / ".gen"
    gen_directory.mkdir(parents=True)
    (gen_directory / "gen.db").write_bytes(b"sqlite")
    (gen_directory / "default.db").write_bytes(b"sqlite")
    monkeypatch.setenv("TOOLUNIVERSE_GEN_ROOT", str(root))
    repository = _FakeRepository(str(repository_path))
    repository.opened_paths = []
    module = ModuleType("gen")

    def open_repository(path):
        repository.opened_paths.append(path)
        return repository

    module.Repository = open_repository
    monkeypatch.setitem(sys.modules, "gen", module)
    return repository_path, repository


def test_branches_view_uses_an_existing_repository_and_validates_its_result(
    monkeypatch, tmp_path
):
    """Load only existing repositories and report the active branch when truncated."""

    repository_path, repository = _authorized_repository(monkeypatch, tmp_path)

    result = _tool().run(
        {"repository_path": "yeast-study", "view": "branches", "limit": 1}
    )

    assert result == {
        "status": "success",
        "data": {
            "view": "branches",
            "branch": None,
            "current_branch": "main",
            "items": [
                {"name": "main", "is_current": True, "head": "abc123", "dirty": False}
            ],
            "returned": 1,
            "total_count": 2,
            "truncated": True,
        },
    }
    assert repository.opened_paths == [str(repository_path)]
    Draft202012Validator(_CONFIG["return_schema"]).validate(result)


def test_operation_view_is_bounded_and_does_not_return_author_or_message(
    monkeypatch, tmp_path
):
    """Use Gen's limit parameter and omit operation author and message text."""

    _repository_path, repository = _authorized_repository(monkeypatch, tmp_path)

    result = _tool().run(
        {
            "repository_path": "yeast-study",
            "view": "operations",
            "branch": "experiment",
            "limit": 2,
        }
    )

    assert result["status"] == "success"
    assert result["data"]["branch"] == "experiment"
    assert result["data"]["returned"] == 2
    assert result["data"]["total_count"] is None
    assert result["data"]["truncated"] is True
    assert repository.operation_query == ("experiment", 3)
    assert result["data"]["items"][0] == {
        "id": "operation-0",
        "parent_id": None,
        "date": "2026-11-20T00:00:00Z",
        "is_head": True,
    }
    assert "committer" not in result["data"]["items"][0]
    assert "email" not in result["data"]["items"][0]
    assert "message" not in result["data"]["items"][0]
    Draft202012Validator(_CONFIG["return_schema"]).validate(result)


def test_sample_view_returns_names_and_collections(monkeypatch, tmp_path):
    """Return sample identifiers and collection names from the repository."""

    _authorized_repository(monkeypatch, tmp_path)
    sample_instances = []

    class FakeSample:
        def __init__(self, name):
            self.name = name
            self.collection = "yeast"
            sample_instances.append(self)

    module = sys.modules["gen"]
    repository = _FakeRepository("unused")
    repository.samples = [FakeSample("reference"), FakeSample("sample-1")]
    module.Repository = lambda path: repository

    result = _tool().run(
        {"repository_path": "yeast-study", "view": "samples", "limit": 10}
    )

    assert result["data"]["items"] == [
        {"name": "reference", "collection": "yeast"},
        {"name": "sample-1", "collection": "yeast"},
    ]
    assert len(sample_instances) == 2
    Draft202012Validator(_CONFIG["return_schema"]).validate(result)


def test_repository_outside_the_configured_root_is_rejected(monkeypatch, tmp_path):
    """Keep a remote caller inside the configured Gen repository root."""

    root = tmp_path / "allowed"
    root.mkdir()
    outside = tmp_path / "outside"
    gen_directory = outside / ".gen"
    gen_directory.mkdir(parents=True)
    (gen_directory / "gen.db").touch()
    (gen_directory / "default.db").touch()
    monkeypatch.setenv("TOOLUNIVERSE_GEN_ROOT", str(root))

    result = _tool().run({"repository_path": str(outside), "view": "branches"})

    assert result["status"] == "error"
    assert "outside the provider directory" in result["error"]


def test_incomplete_repository_is_not_initialized_by_gen(monkeypatch, tmp_path):
    """Reject an incomplete workspace before Gen can initialize it."""

    root = tmp_path / "repositories"
    (root / "incomplete" / ".gen").mkdir(parents=True)
    monkeypatch.setenv("TOOLUNIVERSE_GEN_ROOT", str(root))
    module = ModuleType("gen")
    module.Repository = lambda _path: pytest.fail(
        "Gen must not open an incomplete repository"
    )
    monkeypatch.setitem(sys.modules, "gen", module)

    result = _tool().run({"repository_path": "incomplete", "view": "branches"})

    assert result == {
        "status": "error",
        "error": "the requested directory is not an existing Gen repository",
    }


def test_missing_gen_dependency_has_an_install_hint(monkeypatch, tmp_path):
    """Explain how to add the optional Gen Python package."""

    _authorized_repository(monkeypatch, tmp_path)
    monkeypatch.setitem(sys.modules, "gen", None)

    result = _tool().run({"repository_path": "yeast-study", "view": "branches"})

    assert result["status"] == "error"
    assert "pip install 'gen>=0.5.1'" in result["error"]


def test_default_tool_loading_and_keyword_discovery_find_gen(monkeypatch, tmp_path):
    """Load Gen with defaults, find it by keywords, and execute its wrapper."""

    _authorized_repository(monkeypatch, tmp_path)
    universe = ToolUniverse(load_workspace=False)
    universe.load_tools()

    repository_query = universe.run(
        {
            "name": "Tool_Finder_Keyword",
            "arguments": {
                "description": "inspect local Gen genome version control branches and history",
                "limit": 5,
            },
        }
    )
    assert repository_query[0]["name"] == "Gen_inspect_repository"

    broad_query = universe.run(
        {
            "name": "Tool_Finder_Keyword",
            "arguments": {
                "description": "genome version control repository",
                "limit": 10,
            },
        }
    )
    broad_names = [tool["name"] for tool in broad_query]
    assert broad_names[0] == "Gen_inspect_repository"
    assert "get_gen_info" in broad_names

    result = universe.run(
        {
            "name": "Gen_inspect_repository",
            "arguments": {"repository_path": "yeast-study", "view": "branches"},
        }
    )
    assert result["status"] == "success"
    assert result["data"]["items"][0]["name"] == "main"


def test_gen_software_catalog_is_discoverable_and_works_offline(monkeypatch):
    """Return CLI, Python, and R install/use details without network access."""

    package_config = next(
        entry
        for entry in json.loads(
            (_DATA_ROOT / "packages" / "genomics_tools.json").read_text(
                encoding="utf-8"
            )
        )
        if entry["name"] == "get_gen_info"
    )
    assert package_config["source"] == "https://github.com/genhub-bio/gen"
    assert package_config["license"] == "Apache-2.0"
    assert package_config["author"] == "GenHub Bio"
    assert {"CLI", "Python", "R"} <= set(package_config["tags"])

    def fail_network(*_args, **_kwargs):
        raise OSError("network disabled for this test")

    monkeypatch.setattr("tooluniverse.package_tool.requests.get", fail_network)
    universe = ToolUniverse(load_workspace=False)
    universe.load_tools()

    results = universe.run(
        {
            "name": "Tool_Finder_Keyword",
            "arguments": {
                "description": "Gen standalone command line CLI installation Python R bindings",
                "limit": 5,
            },
        }
    )
    assert results[0]["name"] == "get_gen_info"

    info = universe.run({"name": "get_gen_info", "arguments": {}})

    assert info["package_name"] == "gen"
    assert info["source"] == "local"
    assert info["installation"]["pip"] == "pip install gen"
    assert info["installation"]["conda"] is None
    assert "gen --version" in info["usage_example"]
    assert "gen branch --list" in info["usage_example"]
    assert "gen operations" in info["usage_example"]
    assert "gen list-samples" in info["usage_example"]
    assert "import gen" in info["usage_example"]
    assert "library(genr)" in info["usage_example"]
    assert "repo$get_samples()" in info["usage_example"]
    quick_start = "\n".join(info["quick_start"])
    assert "uv tool install gen" in quick_start
    assert "cargo install gen" in quick_start
    assert "remotes::install_github('genhub-bio/gen', subdir='gen-r')" in quick_start
    assert "github.com/genhub-bio/gen/releases" in quick_start
    assert "R 4.2 or newer" in quick_start


def test_gen_directory_argument_is_rejected_without_opening_it(monkeypatch, tmp_path):
    """Require the workspace root so Gen does not create a nested .gen directory."""

    repository_path, _repository = _authorized_repository(monkeypatch, tmp_path)

    result = _tool().run(
        {"repository_path": str(repository_path / ".gen"), "view": "branches"}
    )

    assert result == {
        "status": "error",
        "error": "pass the Gen workspace directory, not its .gen directory",
    }


def test_empty_database_file_is_rejected_without_opening_it(monkeypatch, tmp_path):
    """Reject empty Gen database placeholders before constructing Repository."""

    root = tmp_path / "repositories"
    gen_directory = root / "empty" / ".gen"
    gen_directory.mkdir(parents=True)
    (gen_directory / "gen.db").touch()
    (gen_directory / "default.db").write_bytes(b"sqlite")
    monkeypatch.setenv("TOOLUNIVERSE_GEN_ROOT", str(root))
    module = ModuleType("gen")
    module.Repository = lambda _path: pytest.fail("Gen must not open an empty database")
    monkeypatch.setitem(sys.modules, "gen", module)

    result = _tool().run({"repository_path": "empty", "view": "branches"})

    assert result == {
        "status": "error",
        "error": "the requested directory is not an existing Gen repository",
    }


def test_gen_directory_symlink_is_rejected(monkeypatch, tmp_path):
    """Prevent a workspace symlink from escaping the approved root."""

    root = tmp_path / "repositories"
    outside_gen = tmp_path / "outside" / ".gen"
    outside_gen.mkdir(parents=True)
    (outside_gen / "gen.db").write_bytes(b"sqlite")
    (outside_gen / "default.db").write_bytes(b"sqlite")
    workspace = root / "symlinked"
    workspace.mkdir(parents=True)
    try:
        (workspace / ".gen").symlink_to(outside_gen, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"directory symlinks are unavailable: {error}")
    monkeypatch.setenv("TOOLUNIVERSE_GEN_ROOT", str(root))
    module = ModuleType("gen")
    module.Repository = lambda _path: pytest.fail(
        "Gen must not open a symlinked .gen directory"
    )
    monkeypatch.setitem(sys.modules, "gen", module)

    result = _tool().run({"repository_path": "symlinked", "view": "branches"})

    assert result == {
        "status": "error",
        "error": "the requested directory is not an existing Gen repository",
    }
