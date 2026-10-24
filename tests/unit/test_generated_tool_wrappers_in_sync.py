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

import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "src/tooluniverse/tools"


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


def _wrapper_names_git_has():
    """Wrapper module names that are *committed*, not merely present on disk.

    ``.exists()`` cannot answer the question this module exists to ask once a
    generator has run in the same checkout: ``.github/workflows/tests.yml``
    runs ``python scripts/build_tools.py`` as a step before pytest, so by the
    time the two tests above execute, a wrapper the commit forgot has already
    been created and they compare regenerated files against regenerated files.
    Git still knows the difference -- a file the generator just made is
    untracked -- and that is what this asks.
    """
    try:
        done = subprocess.run(
            ["git", "ls-files", "-z", "--", "src/tooluniverse/tools"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        pytest.skip("no usable git checkout to ask what is committed")
    names = {
        Path(entry).stem
        for entry in done.stdout.split("\0")
        if entry.endswith(".py") and not entry.endswith("/__init__.py")
    }
    if not names:
        pytest.skip("git lists no wrapper modules; not a source checkout")
    return names


def test_every_builtin_tool_wrapper_is_committed(builtin_tool_names):
    uncommitted = sorted(builtin_tool_names - _wrapper_names_git_has())
    assert not uncommitted, (
        f"{len(uncommitted)} built-in tools have a wrapper on disk that no commit "
        "carries, so `from tooluniverse.tools import ...` raises ImportError for "
        "anyone installing the wheel. Run `python scripts/build_tools.py` and "
        f"`git add src/tooluniverse/tools`. First few: {uncommitted[:10]}"
    )
