"""
The ``SpecialTool`` type: control signals a calling agent loop acts on.

``special_tools.json`` has always declared ``Finish`` and ``CallAgent`` with
``"type": "SpecialTool"``, but no class was ever registered under that name.
Both therefore failed at construction -- ``ToolConfigError: Tool type
'SpecialTool' not found in registry`` -- while still shipping as typed SDK
wrappers in ``tooluniverse.tools.__all__`` and appearing in the generated
documentation with a copy-pasteable ``tu.run(query)`` example that could only
error.

These two entries are not tools that do work. They are the stop and delegate
actions of a multi-step reasoning loop: something a model is offered so it can
tell *its own* loop what to do next. ToolUniverse runs no such loop, and
inventing one here would be inventing a feature. So the type resolves to the
only honest behaviour available: echo the signal back, state plainly that
nothing was executed and no data was retrieved, and say what the caller's loop
is expected to do with it.
"""

from typing import Any, Dict, Optional

from .base_tool import BaseTool
from .tool_registry import register_tool

# What the caller's own loop is expected to do when a signal comes back.
_EXPECTED_OF_CALLER = {
    "Finish": "stop the current multi-step reasoning chain",
    "CallAgent": (
        "execute the plan in arguments['solution'] yourself, as a new reasoning chain"
    ),
}

_GENERIC_EXPECTATION = "decide what to do next; ToolUniverse did nothing"


@register_tool("SpecialTool")
class SpecialTool(BaseTool):
    """Echo a control signal back to the loop that raised it.

    Deliberately performs no work. ``performed_work`` is a constant ``false``
    so that a caller which inspects the result cannot mistake it for data, and
    the arguments come back unchanged so a loop can read the plan it sent.
    """

    def run(self, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        name = (self.tool_config or {}).get("name") or "SpecialTool"
        expectation = _EXPECTED_OF_CALLER.get(name, _GENERIC_EXPECTATION)
        return {
            "control_signal": name,
            "performed_work": False,
            "arguments": dict(arguments or {}),
            "message": (
                f"{name} is a control signal, not an executable tool. "
                "ToolUniverse queried nothing and returns no data. The agent "
                f"loop that offered {name} to its model is responsible for "
                f"acting on it: {expectation}."
            ),
        }
