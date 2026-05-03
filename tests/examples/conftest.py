"""
Fixtures for tests/examples/ — provide a minimal ToolUniverse instance
that includes only the tools registered via @register_tool decorators in the
example modules (no built-in JSON configs are loaded, so tests stay fast and
require no external API keys or network access).
"""

import pytest


@pytest.fixture
def tu(tmp_path, monkeypatch):
    """Minimal ToolUniverse with auto-discovered custom tools only.

    Loads tools registered via @register_tool at module import time, but
    skips all built-in JSON category files.  File-writing tests are
    isolated to a temporary directory.
    """
    monkeypatch.chdir(tmp_path)

    from tooluniverse import ToolUniverse

    # tool_files={} + keep_default_tools=False → no JSON category files loaded.
    # load_tools() still calls _load_auto_discovered_configs(), which picks up
    # every @register_tool(config=...) registered while pytest collected the
    # example modules.
    instance = ToolUniverse(tool_files={}, keep_default_tools=False)
    instance.load_tools(categories=[])

    yield instance

    try:
        instance.close()
    except Exception:
        pass
