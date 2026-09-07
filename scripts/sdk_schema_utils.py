"""Reusable helpers for generating ToolUniverse schemas from typed SDK models."""

from __future__ import annotations

import importlib
import json
from copy import deepcopy
from typing import Any, Mapping, Sequence

from pydantic import TypeAdapter


def _resolve_local_ref(schema: dict[str, Any], ref: str) -> Any:
    """Resolve a local JSON Pointer emitted by Pydantic."""

    if not ref.startswith("#/"):
        raise ValueError(f"Expected a local JSON Pointer, got {ref!r}")
    target: Any = schema
    for raw_token in ref[2:].split("/"):
        token = raw_token.replace("~1", "/").replace("~0", "~")
        target = target[token]
    return target


def _expose_root_union_properties(schema: dict[str, Any]) -> None:
    """Expose object fields when an SDK params alias is a root-level union.

    Pydantic represents ``Union[TypedDict, TypedDict]`` as root ``anyOf`` refs.
    ToolUniverse also needs a top-level ``properties`` map to build callable
    signatures and discovery metadata. The original union remains authoritative
    and the merged properties are an additional common interface constraint.
    """

    choices = schema.get("anyOf") or schema.get("oneOf")
    if not isinstance(choices, list):
        return

    branches: list[dict[str, Any]] = []
    for choice in choices:
        if not isinstance(choice, dict):
            return
        branch = choice
        if set(choice) == {"$ref"}:
            branch = _resolve_local_ref(schema, choice["$ref"])
        if not isinstance(branch, dict) or branch.get("type") != "object":
            return
        branches.append(branch)

    candidates: dict[str, list[dict[str, Any]]] = {}
    for branch in branches:
        for name, property_schema in branch.get("properties", {}).items():
            candidates.setdefault(name, []).append(property_schema)

    properties: dict[str, Any] = {}
    for name, variants in candidates.items():
        unique: list[dict[str, Any]] = []
        fingerprints: set[str] = set()
        for variant in variants:
            fingerprint = json.dumps(variant, sort_keys=True)
            if fingerprint not in fingerprints:
                fingerprints.add(fingerprint)
                unique.append(deepcopy(variant))
        properties[name] = unique[0] if len(unique) == 1 else {"anyOf": unique}

    common_required = set(branches[0].get("required", []))
    for branch in branches[1:]:
        common_required.intersection_update(branch.get("required", []))

    schema["type"] = "object"
    schema["properties"] = properties
    if common_required:
        schema["required"] = [
            name for name in branches[0].get("required", []) if name in common_required
        ]


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
    _expose_root_union_properties(schema)
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
