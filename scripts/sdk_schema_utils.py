"""Reusable helpers for generating ToolUniverse schemas from typed SDK models."""

from __future__ import annotations

import importlib
from typing import Any, Mapping, Sequence

from pydantic import TypeAdapter


def typed_dict_params_schema(
    module_name: str | None,
    *,
    positional: Sequence[str] = (),
    descriptions: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Build an object schema from a typed SDK ``*Params`` model.

    ``module_name`` may be omitted for SDK operations without a parameter
    model. Positional path identifiers are added when the SDK represents them
    only in the method signature rather than in its params TypedDict.
    """

    if module_name:
        module = importlib.import_module(module_name)
        params_names = [name for name in module.__all__ if name.endswith("Params")]
        if len(params_names) != 1:
            raise ValueError(
                f"Expected exactly one *Params export in {module_name}, "
                f"found {params_names}"
            )
        schema = TypeAdapter(getattr(module, params_names[0])).json_schema()
    else:
        schema = {"type": "object", "properties": {}}

    schema.pop("title", None)
    schema["additionalProperties"] = False
    properties = schema.setdefault("properties", {})
    required = schema.setdefault("required", [])
    for name in reversed(positional):
        properties.setdefault(name, {"type": "string", "minLength": 1})
        if name not in required:
            required.insert(0, name)

    for name, description in (descriptions or {}).items():
        if name in properties:
            properties[name].setdefault("description", description)
    if not required:
        schema.pop("required", None)
    return schema
