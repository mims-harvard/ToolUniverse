"""Every registered tool must be reachable from the Python SDK.

The wrappers under ``tooluniverse/tools`` are generated from the tool configs
by ``scripts/build_tools.py``. Nothing re-ran that build when tools were
added, and nothing noticed: 119 registered tools -- including
``gather_drug_profile`` and ``SCP_search_studies`` -- had no wrapper at all,
so ``from tooluniverse.tools import ...`` raised ImportError for 4% of the
catalogue while the CLI and MCP served them normally.

This compares the registry against the generated package directly, which is
fast, rather than re-running the generator.
"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

TOOLS_DIR = Path(__file__).resolve().parents[2] / "src/tooluniverse/tools"


@pytest.fixture(scope="module")
def registered_tool_names():
    from tooluniverse import ToolUniverse

    engine = ToolUniverse()
    engine.load_tools()
    return set(engine.all_tool_dict)


def test_every_registered_tool_has_a_generated_wrapper(registered_tool_names):
    missing = sorted(
        name
        for name in registered_tool_names
        if not (TOOLS_DIR / f"{name}.py").exists()
    )
    assert not missing, (
        f"{len(missing)} registered tools have no generated wrapper; "
        f"run `python scripts/build_tools.py`. First few: {missing[:10]}"
    )


def test_every_registered_tool_is_importable_from_the_sdk(registered_tool_names):
    from tooluniverse import tools as sdk

    missing = sorted(name for name in registered_tool_names if not hasattr(sdk, name))
    assert not missing, (
        f"{len(missing)} registered tools are not exported by tooluniverse.tools; "
        f"run `python scripts/build_tools.py`. First few: {missing[:10]}"
    )
