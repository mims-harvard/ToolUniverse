from __future__ import annotations

from typing import Any, Dict

from .common_utils import read_json, write_json, vsd_generated_path


def _normalize_catalog(data: Any) -> Dict[str, Dict[str, Any]]:
    catalog: Dict[str, Dict[str, Any]] = {}
    if not isinstance(data, dict):
        return catalog

    generated = data.get("generated_tools") if isinstance(data.get("generated_tools"), list) else None
    if generated is not None:
        for item in generated:
            if isinstance(item, dict) and item.get("name"):
                name = item["name"]
                catalog[name] = dict(item)
        return catalog

    for name, cfg in data.items():
        if not isinstance(cfg, dict):
            continue
        entry = dict(cfg)
        entry.setdefault("name", name)
        catalog[name] = entry
    return catalog


def load_catalog() -> Dict[str, Dict[str, Any]]:
    """
    Load the Verified Source catalog from disk and normalize it
    to a {name: config} dictionary regardless of historical format.
    """
    path = vsd_generated_path()
    data = read_json(path, {})
    return _normalize_catalog(data)


def save_catalog(catalog: Dict[str, Dict[str, Any]]) -> str:
    """
    Persist the catalog to disk as a flat {name: config} mapping.
    Returns the file path for convenience.
    """
    path = vsd_generated_path()
    # ensure each entry has its name
    serializable = {name: dict(cfg, name=name) for name, cfg in catalog.items()}
    write_json(path, serializable)
    return path


def upsert_tool(tool_name: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Insert or update a tool configuration in the catalog and propagate the
    change to any in-process dynamic registries.
    """
    catalog = load_catalog()
    config = dict(cfg)
    config.setdefault("name", tool_name)
    catalog[tool_name] = config
    save_catalog(catalog)

    # Notify dynamic REST runner (best-effort, optional import)
    try:
        from .dynamic_rest_runner import upsert_generated_tool  # type: ignore

        upsert_generated_tool(tool_name, config)
    except Exception:
        pass

    return config


def remove_tool(tool_name: str) -> bool:
    """
    Remove a tool from the catalog. Returns True if a tool was removed.
    """
    catalog = load_catalog()
    if tool_name not in catalog:
        return False
    del catalog[tool_name]
    save_catalog(catalog)

    try:
        from .dynamic_rest_runner import remove_generated_tool  # type: ignore

        remove_generated_tool(tool_name)
    except Exception:
        pass

    return True
