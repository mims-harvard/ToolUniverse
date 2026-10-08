"""A tool file's neighbours must import wherever `tu serve` is started.

Measured: a my_tool.py that does `import helpers` from its own folder served fine from that
folder and failed with "No module named 'helpers'" from anywhere else -- which is where the
background service the Remote servers page offers starts.
"""

from __future__ import annotations

import sys
import textwrap
from types import SimpleNamespace

import pytest

from tooluniverse import cli


def test_a_neighbouring_module_imports_from_another_folder(tmp_path, monkeypatch):
    from tooluniverse import mcp_tool_registry as registry

    project = tmp_path / "project"
    project.mkdir()
    (project / "lab_helpers_7f3a.py").write_text("def score(s):\n    return len(s)\n")
    (project / "my_tool.py").write_text(textwrap.dedent('''
        from tooluniverse.mcp_tool_registry import remote_tool
        import lab_helpers_7f3a

        @remote_tool
        def predict(sequence: str) -> dict:
            """Score one sequence."""
            return {"score": lab_helpers_7f3a.score(sequence)}
    '''))
    elsewhere = tmp_path / "home"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.setattr(registry, "_start_server_for_port", lambda port: None)
    saved = dict(registry._mcp_tool_registry)
    args = SimpleNamespace(files=[str(project / "my_tool.py")], port=8399, host="127.0.0.1",
                           name=None, workers=1, share=False)
    try:
        cli._start_remote_tool_server(args)
        assert "predict" in registry._mcp_tool_registry
    finally:
        registry._mcp_tool_registry.clear()
        registry._mcp_tool_registry.update(saved)
        sys.modules.pop("lab_helpers_7f3a", None)
