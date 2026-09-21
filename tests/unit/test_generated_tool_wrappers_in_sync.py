"""Every built-in tool must be reachable from the Python SDK.

The wrappers under ``tooluniverse/tools`` are generated from the shipped tool
configs by ``scripts/build_tools.py``. Nothing re-ran that build when tools
were added, and nothing noticed: 119 built-in tools -- including
``gather_drug_profile`` and ``SCP_search_studies`` -- had no wrapper at all,
so ``from tooluniverse.tools import ...`` raised ImportError for 4% of the
catalogue while the CLI and MCP served them normally.

The tool list mirrors what the generator itself writes wrappers for: names
that appear in the shipped configs *and* load into the registry. The configs
alone list 2935 tools while 2718 load, the rest needing credentials or
optional dependencies; the registry alone picks up tools that tests register
at runtime, such as ``_echo_tool``. Only the intersection is the set that
should have wrappers.
"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

TOOLS_DIR = Path(__file__).resolve().parents[2] / "src/tooluniverse/tools"


@pytest.fixture(scope="module")
def builtin_tool_names():
    from tooluniverse import ToolUniverse
    from tooluniverse.default_config import default_tool_files
    from tooluniverse.utils import read_json_list

    configured = set()
    for path in default_tool_files.values():
        try:
            entries = read_json_list(path)
        except Exception:
            continue
        for entry in entries:
            name = entry.get("name") if isinstance(entry, dict) else None
            if name:
                configured.add(name)
    assert configured, "no built-in tool configs were readable"

    engine = ToolUniverse()
    engine.load_tools()
    names = configured & set(engine.all_tool_dict)
    assert names, "no configured tool loaded into the registry"
    return names


def test_every_builtin_tool_has_a_generated_wrapper(builtin_tool_names):
    missing = sorted(
        name for name in builtin_tool_names if not (TOOLS_DIR / f"{name}.py").exists()
    )
    assert not missing, (
        f"{len(missing)} built-in tools have no generated wrapper; "
        f"run `python scripts/build_tools.py`. First few: {missing[:10]}"
    )


def test_every_builtin_tool_is_importable_from_the_sdk(builtin_tool_names):
    from tooluniverse import tools as sdk

    missing = sorted(name for name in builtin_tool_names if not hasattr(sdk, name))
    assert not missing, (
        f"{len(missing)} built-in tools are not exported by tooluniverse.tools; "
        f"run `python scripts/build_tools.py`. First few: {missing[:10]}"
    )
