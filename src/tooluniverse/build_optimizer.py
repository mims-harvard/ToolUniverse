"""Build optimization utilities for ToolUniverse tools."""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Set, Tuple

# Fields excluded from hash calculation and comparison (metadata/timestamp fields)
_EXCLUDED_FIELDS = frozenset(
    {"timestamp", "last_updated", "created_at", "_cache", "_metadata"}
)


def _normalize_value(value: Any) -> Any:
    """Recursively normalize values for consistent hashing."""
    if isinstance(value, dict):
        # Sort dictionary keys and normalize values
        return {k: _normalize_value(v) for k, v in sorted(value.items())}
    elif isinstance(value, list):
        # Normalize list elements
        return [_normalize_value(item) for item in value]
    elif isinstance(value, (str, int, float, bool)) or value is None:
        return value
    else:
        # Convert other types to string representation for hashing
        return str(value)


def calculate_tool_hash(tool_config: Dict[str, Any], verbose: bool = False) -> str:
    """Calculate a hash for tool configuration to detect changes.

    Args:
        tool_config: Tool configuration dictionary
        verbose: If True, print excluded fields (for debugging)

    Returns:
        MD5 hash string of the normalized configuration
    """
    # Create a normalized version of the config for hashing
    normalized_config = {}
    excluded_values = []

    for key, value in sorted(tool_config.items()):
        if key not in _EXCLUDED_FIELDS:
            # Recursively normalize nested structures
            normalized_config[key] = _normalize_value(value)
        elif verbose:
            excluded_values.append(key)

    if verbose and excluded_values:
        print(f"  Excluded fields from hash: {', '.join(excluded_values)}")

    # Use consistent JSON serialization with sorted keys
    config_str = json.dumps(
        normalized_config, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.md5(config_str.encode("utf-8")).hexdigest()


def load_metadata(metadata_file: Path) -> Dict[str, str]:
    """Load tool metadata from file."""
    if not metadata_file.exists():
        return {}

    try:
        with open(metadata_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_metadata(metadata: Dict[str, str], metadata_file: Path) -> None:
    """Save tool metadata to file."""
    metadata_file.parent.mkdir(parents=True, exist_ok=True)
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, sort_keys=True)


def cleanup_orphaned_files(tools_dir: Path, current_tool_names: Set[str]) -> int:
    """Remove files for tools that no longer exist."""
    if not tools_dir.exists():
        return 0

    cleaned_count = 0
    keep_files = {"__init__", "_shared_client", "__pycache__"}

    for file_path in tools_dir.iterdir():
        if (
            file_path.is_file()
            and file_path.suffix == ".py"
            and file_path.stem not in keep_files
            and file_path.stem not in current_tool_names
        ):
            print(f"🗑️  Removing orphaned tool file: {file_path.name}")
            file_path.unlink()
            cleaned_count += 1

    return cleaned_count


def _compare_configs(old_config: Dict[str, Any], new_config: Dict[str, Any]) -> list:
    """Compare two configs and return list of changed field paths."""
    changes = []

    all_keys = set(old_config.keys()) | set(new_config.keys())

    for key in all_keys:
        if key in _EXCLUDED_FIELDS:
            continue

        old_val = old_config.get(key)
        new_val = new_config.get(key)

        if old_val != new_val:
            changes.append(key)

    return changes


def get_changed_tools(
    current_tools: Dict[str, Any],
    metadata_file: Path,
    force_regenerate: bool = False,
    verbose: bool = False,
) -> Tuple[list, list, list, Dict[str, list]]:
    """Get lists of new, changed, and unchanged tools.

    Args:
        current_tools: Dictionary of current tool configurations
        metadata_file: Path to metadata file storing previous hashes
        force_regenerate: If True, mark all tools as changed
        verbose: If True, provide detailed change information

    Returns:
        Tuple of (new_tools, changed_tools, unchanged_tools, change_details)
        where change_details maps tool_name -> list of changed field names
    """
    old_metadata = load_metadata(metadata_file)
    new_metadata = {}
    new_tools = []
    changed_tools = []
    unchanged_tools = []
    change_details: Dict[str, list] = {}

    if force_regenerate:
        print("🔄 Force regeneration enabled - all tools will be regenerated")
        for tool_name, tool_config in current_tools.items():
            current_hash = calculate_tool_hash(tool_config, verbose=verbose)
            new_metadata[tool_name] = current_hash
            if tool_name in old_metadata:
                changed_tools.append(tool_name)
                change_details[tool_name] = ["force_regenerate"]
            else:
                new_tools.append(tool_name)
    else:
        for tool_name, tool_config in current_tools.items():
            current_hash = calculate_tool_hash(tool_config, verbose=verbose)
            new_metadata[tool_name] = current_hash

            old_hash = old_metadata.get(tool_name)
            if old_hash is None:
                new_tools.append(tool_name)
                if verbose:
                    print(f"  ✨ New tool detected: {tool_name}")
            elif old_hash != current_hash:
                changed_tools.append(tool_name)
                # Try to identify which fields changed (if we have the old config)
                # Note: We only have hashes, so we can't do detailed field comparison
                # This would require storing full configs, which we avoid for size reasons
                change_details[tool_name] = ["hash_mismatch"]
                if verbose:
                    print(
                        f"  🔄 Tool changed: {tool_name} (hash: {old_hash[:8]}... -> {current_hash[:8]}...)"
                    )
            else:
                unchanged_tools.append(tool_name)

    # Save updated metadata
    save_metadata(new_metadata, metadata_file)

    return new_tools, changed_tools, unchanged_tools, change_details
