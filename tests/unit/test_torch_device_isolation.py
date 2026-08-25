import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


pytestmark = pytest.mark.unit

SOURCE_ROOT = Path(__file__).parents[2] / "src" / "tooluniverse"


def test_tooluniverse_never_mutates_torch_global_default_device():
    offenders = []
    for path in SOURCE_ROOT.rglob("*.py"):
        if "set_default_device(" in path.read_text(encoding="utf-8"):
            offenders.append(path.relative_to(SOURCE_ROOT).as_posix())

    assert offenders == [], (
        "ToolUniverse shares one Python process across many tools, so changing "
        "PyTorch's process-wide default device can crash unrelated tools or mix "
        f"CPU and GPU tensors. Offending modules: {offenders}"
    )


@pytest.mark.parametrize("light_import", ["true", "false"])
def test_import_does_not_load_faiss_before_torch(light_import):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SOURCE_ROOT.parent)
    env["TOOLUNIVERSE_LIGHT_IMPORT"] = light_import

    script = """
import importlib.util
import sys

import tooluniverse

assert "faiss" not in sys.modules, "faiss was imported eagerly"
if importlib.util.find_spec("torch") is not None:
    import torch

    assert torch.zeros(1, 4, 524_288).shape == (1, 4, 524_288)
"""

    result = subprocess.run(
        [sys.executable, "-c", script],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr


def test_subpackage_discovery_skips_builtins_but_keeps_external_paths(
    tmp_path, monkeypatch
):
    from tooluniverse import tool_registry

    main_root = tmp_path / "main" / "tooluniverse"
    duplicate_main_root = tmp_path / "installed_main" / "tooluniverse"
    external_root = tmp_path / "external" / "tooluniverse"
    for package in (
        main_root / "builtin",
        duplicate_main_root / "duplicate_builtin",
        external_root / "contributed",
    ):
        package.mkdir(parents=True)
        (package / "__init__.py").write_text("", encoding="utf-8")
    (main_root / "__init__.py").write_text("", encoding="utf-8")
    (duplicate_main_root / "execute_function.py").write_text("", encoding="utf-8")
    (duplicate_main_root / "tool_registry.py").write_text("", encoding="utf-8")

    package = SimpleNamespace(
        __file__=str(main_root / "__init__.py"),
        __path__=[str(main_root), str(duplicate_main_root), str(external_root)],
    )
    imported = []

    def fake_import(name):
        if name == "example_package":
            return package
        imported.append(name)
        return SimpleNamespace()

    monkeypatch.setattr(tool_registry.importlib, "import_module", fake_import)

    tool_registry._auto_import_subpackages("example_package")

    assert imported == ["example_package.contributed"]
