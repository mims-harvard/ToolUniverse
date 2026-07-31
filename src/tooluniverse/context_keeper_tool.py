from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from .tool_registry import register_tool

CONTEXT_DIR = os.path.join(os.path.expanduser("~"), ".tooluniverse", "context")
CONTEXT_PATH = os.path.join(CONTEXT_DIR, "context.json")


def _ensure_dir() -> None:
    os.makedirs(CONTEXT_DIR, exist_ok=True)


def _load_context() -> Dict[str, Any]:
    if not os.path.exists(CONTEXT_PATH):
        return {}
    try:
        with open(CONTEXT_PATH, "r", encoding="utf-8") as handle:
            data = json.load(handle)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


def _write_context(data: Dict[str, Any]) -> None:
    _ensure_dir()
    tmp_path = f"{CONTEXT_PATH}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
    os.replace(tmp_path, CONTEXT_PATH)


@register_tool("ContextKeeperTool")
class ContextKeeperTool:
    """
    Lightweight context store that agents can use to persist conversation or task state
    between ToolUniverse calls. Data is saved under ~/.tooluniverse/context/context.json.
    """

    name = "ContextKeeperTool"
    description = "Persist or retrieve task context (key/value pairs) for ongoing agent workflows."
    input_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["get", "set", "append", "clear", "keys"],
                "default": "get",
            },
            "key": {"type": "string", "description": "Context entry name"},
            "value": {
                "description": "Value to store; for append operations this should be a list item.",
            },
        },
        "additionalProperties": False,
    }

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        action = (arguments.get("action") or "get").lower()
        key: Optional[str] = arguments.get("key")
        value: Any = arguments.get("value")

        context = _load_context()

        if action == "keys":
            return {"ok": True, "keys": sorted(context.keys())}

        if action == "clear":
            if key:
                removed = context.pop(key, None) is not None
                _write_context(context)
                return {"ok": removed, "cleared": key if removed else None}
            context.clear()
            _write_context(context)
            return {"ok": True, "cleared": "all"}

        if action == "set":
            if key is None:
                return {"ok": False, "error": "key is required for set"}
            context[key] = value
            _write_context(context)
            return {"ok": True, "key": key, "value": value}

        if action == "append":
            if key is None:
                return {"ok": False, "error": "key is required for append"}
            existing = context.get(key)
            if existing is None:
                context[key] = [value]
            elif isinstance(existing, list):
                existing.append(value)
            else:
                context[key] = [existing, value]
            _write_context(context)
            return {"ok": True, "key": key, "value": context[key]}

        # default: get
        if key:
            return {"ok": True, "key": key, "value": context.get(key)}
        return {"ok": True, "value": context}
