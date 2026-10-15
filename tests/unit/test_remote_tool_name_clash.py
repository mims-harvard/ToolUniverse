"""`from tooluniverse import remote_tool` must stay the decorator.

The RemoteTool placeholder class lived in a submodule also named remote_tool. Importing a
submodule makes Python set it as an attribute of the package, so once anything looked up the
RemoteTool class -- instantiating one of the bundled remote tool configs does -- the package's
remote_tool was the submodule, and a scientist's

    from tooluniverse import remote_tool

    @remote_tool
    def predict(...): ...

failed with "TypeError: 'module' object is not callable".
"""

from __future__ import annotations

import importlib


def test_looking_up_the_remote_tool_class_keeps_the_decorator():
    from tooluniverse.tool_registry import get_tool_class_lazy

    cls = get_tool_class_lazy("RemoteTool")
    assert cls is not None and cls.__name__ == "RemoteTool"

    import tooluniverse

    assert callable(tooluniverse.remote_tool)
    assert not isinstance(tooluniverse.remote_tool, type(importlib))


def test_the_decorator_still_decorates_after_the_lookup():
    from tooluniverse.tool_registry import get_tool_class_lazy

    get_tool_class_lazy("RemoteTool")
    from tooluniverse import mcp_tool_registry as registry
    from tooluniverse import remote_tool

    saved = dict(registry._mcp_tool_registry)
    try:
        @remote_tool
        def predict(sequence: str) -> dict:
            """Score one sequence."""
            return {}

        assert "predict" in registry._mcp_tool_registry
    finally:
        registry._mcp_tool_registry.clear()
        registry._mcp_tool_registry.update(saved)
