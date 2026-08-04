import ast
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import tooluniverse


pytestmark = pytest.mark.unit
PACKAGE_DIR = Path(__file__).parents[2] / "src" / "tooluniverse"


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, PACKAGE_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


coding = _load("generator_invariants_coding", "generate_coding_api.py")
lazy = _load("generator_invariants_lazy", "generate_lazy_registry.py")


@pytest.mark.parametrize(
    ("original", "safe"),
    [
        ("dist-max", "dist_max"),
        ("from", "from_"),
        ("2d", "_2d"),
        ("gene.symbol", "gene_symbol"),
        ("", "parameter"),
        ("stream_callback", "stream_callback_"),
        ("use_cache", "use_cache_"),
        ("validate", "validate_"),
    ],
)
def test_parameter_names_are_valid_and_do_not_shadow_controls(original, safe):
    assert coding._safe_param(original) == safe
    assert safe.isidentifier()


def test_wrapper_with_api_use_cache_parameter_is_valid_python():
    source = coding._generate_wrapper(
        "ExampleTool",
        {
            "description": "Example",
            "parameter": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "use_cache": {"type": "boolean"},
                },
                "required": ["query"],
            },
        },
    )

    ast.parse(source)
    assert "use_cache_: Optional[bool] = None" in source
    assert '"use_cache": use_cache_' in source
    assert "use_cache: bool = False" in source


def test_wrapper_rejects_collisions_after_sanitization():
    config = {
        "parameter": {
            "properties": {
                "gene-symbol": {"type": "string"},
                "gene_symbol": {"type": "string"},
            }
        }
    }

    with pytest.raises(ValueError, match="Parameter name collision"):
        coding._generate_wrapper("ExampleTool", config)


@pytest.mark.parametrize(
    ("name", "valid"),
    [
        ("UniProt_search", True),
        ("class", False),
        ("2D_view", False),
        ("_private", False),
        ("not-a-name", False),
    ],
)
def test_tool_names_must_be_public_python_identifiers(name, valid):
    assert coding._is_valid_tool_name(name) is valid


def test_description_cleaning_produces_safe_single_line_docstrings():
    cleaned = coding._clean_desc('Path C:\\Users\nwith  """quotes"""')

    assert "\n" not in cleaned
    assert "C:\\\\Users" in cleaned
    assert '"""' not in cleaned


def test_write_if_changed_is_idempotent(tmp_path):
    path = tmp_path / "wrapper.py"

    assert coding._write_if_changed(path, "first\n") is True
    first_mtime = path.stat().st_mtime_ns
    assert coding._write_if_changed(path, "first\n") is False
    assert path.stat().st_mtime_ns == first_mtime
    assert coding._write_if_changed(path, "second\n") is True


def test_init_generation_is_sorted_and_includes_handwritten_public_wrappers(tmp_path):
    (tmp_path / "ManualTool.py").write_text(
        "def ManualTool(): pass\n", encoding="utf-8"
    )

    with patch.object(coding, "_TOOLS_DIR", tmp_path):
        source = coding._generate_init(["ZetaTool", "AlphaTool"])

    ast.parse(source)
    assert source.index("from .AlphaTool") < source.index("from .ManualTool")
    assert source.index("from .ManualTool") < source.index("from .ZetaTool")


def test_full_generation_preserves_handwritten_files_removes_stale_output_and_is_idempotent(
    tmp_path,
):
    shared = tmp_path / "_shared_client.py"
    manual = tmp_path / "ManualTool.py"
    stale = tmp_path / "OldTool.py"
    shared.write_text("def get_shared_client(): pass\n", encoding="utf-8")
    manual.write_text("def ManualTool(): pass\n", encoding="utf-8")
    stale.write_text(f"{coding._MARKER}\nold = True\n", encoding="utf-8")

    class FakeToolUniverse:
        def __init__(self):
            self.all_tools = ["ExampleTool"]
            self.all_tool_dict = {
                "ExampleTool": {
                    "description": "Generated safely",
                    "parameter": {"properties": {"use_cache": {"type": "boolean"}}},
                }
            }

        def load_tools(self):
            return None

    completed = SimpleNamespace(returncode=0, stdout="")
    with (
        patch.object(coding, "_TOOLS_DIR", tmp_path),
        patch.object(tooluniverse, "ToolUniverse", FakeToolUniverse),
        patch("subprocess.run", return_value=completed),
    ):
        coding.main()
        first_contents = {
            path.name: path.read_text(encoding="utf-8")
            for path in tmp_path.glob("*.py")
        }
        coding.main()
        second_contents = {
            path.name: path.read_text(encoding="utf-8")
            for path in tmp_path.glob("*.py")
        }

    assert shared.is_file()
    assert manual.is_file()
    assert not stale.exists()
    assert ast.parse((tmp_path / "ExampleTool.py").read_text(encoding="utf-8"))
    assert first_contents == second_contents


def test_static_registry_source_is_sorted_importable_and_deterministic():
    registry = {"ZetaTool": "zeta", "AlphaTool": "alpha"}

    first = lazy.render_static_registry(registry)
    second = lazy.render_static_registry(dict(reversed(list(registry.items()))))
    namespace = {}
    exec(compile(first, "_lazy_registry_static.py", "exec"), namespace)

    assert first == second
    assert first.index('"AlphaTool"') < first.index('"ZetaTool"')
    assert namespace["STATIC_LAZY_REGISTRY"] == registry


def test_static_registry_main_writes_the_discovered_mapping():
    registry = {"ExampleTool": "example_tool"}

    with (
        patch.object(lazy, "build_lazy_registry", return_value=registry),
        patch.object(Path, "write_text") as write_text,
    ):
        lazy.main()

    content = write_text.call_args.args[0]
    namespace = {}
    exec(compile(content, "_lazy_registry_static.py", "exec"), namespace)
    assert namespace["STATIC_LAZY_REGISTRY"] == registry
    assert write_text.call_args.kwargs == {"encoding": "utf-8"}
