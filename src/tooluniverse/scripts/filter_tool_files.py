#!/usr/bin/env python3
"""
Script to filter tool files by removing tools that don't exist in the current tool universe.

This script:
1. Gets all valid tool names from ToolUniverse using scan_all=True
2. Filters tool_relationship_graph_FINAL.json to keep only valid tools
3. Filters v4_all_tools_final.json to keep only valid tools
4. Preserves all other data structure and content
"""

import json
from pathlib import Path

# Import after modifying sys.path
from tooluniverse import ToolUniverse


def load_json_file(file_path):
    """Load JSON file and return the data."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return None


def save_json_file(file_path, data):
    """Save data to JSON file."""
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Successfully saved filtered data to {file_path}")
        return True
    except Exception as e:
        print(f"Error saving {file_path}: {e}")
        return False


def filter_tool_relationship_graph(data, valid_tool_names):
    """
    Filter tool_relationship_graph_FINAL.json to keep only valid tools.

    Args:
        data: The loaded JSON data
        valid_tool_names: Set of valid tool names

    Returns
        Filtered data
    """
    if not isinstance(data, dict):
        print("Warning: tool_relationship_graph data is not a dict")
        return data

    filtered_data = {}

    # Handle nodes array
    if "nodes" in data and isinstance(data["nodes"], list):
        filtered_nodes = []
        for node in data["nodes"]:
            if isinstance(node, dict) and "name" in node:
                if node["name"] in valid_tool_names:
                    filtered_nodes.append(node)
                else:
                    print(f"Removing node from relationship graph: {node['name']}")
            else:
                # Keep non-tool nodes (if any)
                filtered_nodes.append(node)
        filtered_data["nodes"] = filtered_nodes
        print(
            f"Nodes: {len(data['nodes'])} -> {len(filtered_nodes)} ({len(data['nodes']) - len(filtered_nodes)} removed)"
        )

    # Handle edges array
    if "edges" in data and isinstance(data["edges"], list):
        filtered_edges = []
        for edge in data["edges"]:
            if isinstance(edge, dict) and "source" in edge and "target" in edge:
                # Keep edge if both source and target are valid tools
                if (
                    edge["source"] in valid_tool_names
                    and edge["target"] in valid_tool_names
                ):
                    filtered_edges.append(edge)
                else:
                    print(
                        f"Removing edge from relationship graph: {edge.get('source', 'unknown')} -> {edge.get('target', 'unknown')}"
                    )
            else:
                # Keep non-tool edges (if any)
                filtered_edges.append(edge)
        filtered_data["edges"] = filtered_edges
        print(
            f"Edges: {len(data['edges'])} -> {len(filtered_edges)} ({len(data['edges']) - len(filtered_edges)} removed)"
        )

    # Keep other fields as-is (like stats, metadata, etc.)
    for key, value in data.items():
        if key not in ["nodes", "edges"]:
            filtered_data[key] = value

    return filtered_data


def filter_v4_all_tools(data, valid_tool_names):
    """
    Filter v4_all_tools_final.json to keep only valid tools.

    Args:
        data: The loaded JSON data
        valid_tool_names: Set of valid tool names

    Returns
        Filtered data
    """
    if not isinstance(data, list):
        print("Warning: v4_all_tools data is not a list")
        return data

    filtered_data = []

    for tool in data:
        if isinstance(tool, dict) and "name" in tool:
            if tool["name"] in valid_tool_names:
                filtered_data.append(tool)
            else:
                print(f"Removing tool from v4_all_tools: {tool['name']}")
        else:
            # Keep non-tool entries (if any)
            filtered_data.append(tool)

    return filtered_data


def main():
    """Main function to filter the tool files."""
    print("Starting tool file filtering process...")

    # Initialize ToolUniverse and get all valid tool names
    print("Getting all valid tool names from ToolUniverse...")
    tu = ToolUniverse()
    all_tool_names = tu.list_built_in_tools(mode="list_name", scan_all=True)
    valid_tool_names = set(all_tool_names)
    print(f"Found {len(valid_tool_names)} valid tools")

    # Define file paths
    project_root = Path(__file__).parent.parent.parent.parent
    web_dir = project_root / "web"

    relationship_graph_file = web_dir / "tool_relationship_graph_FINAL.json"
    v4_tools_file = web_dir / "v4_all_tools_final.json"

    # Check if files exist
    if not relationship_graph_file.exists():
        print(f"Error: {relationship_graph_file} not found")
        return

    if not v4_tools_file.exists():
        print(f"Error: {v4_tools_file} not found")
        return

    # Process tool_relationship_graph_FINAL.json
    print(f"\nProcessing {relationship_graph_file.name}...")
    relationship_data = load_json_file(relationship_graph_file)
    if relationship_data is not None:
        filtered_relationship_data = filter_tool_relationship_graph(
            relationship_data, valid_tool_names
        )

        # Save filtered data
        save_json_file(relationship_graph_file, filtered_relationship_data)

    # Process v4_all_tools_final.json
    print(f"\nProcessing {v4_tools_file.name}...")
    v4_data = load_json_file(v4_tools_file)
    if v4_data is not None:
        original_count = len(v4_data)
        filtered_v4_data = filter_v4_all_tools(v4_data, valid_tool_names)
        filtered_count = len(filtered_v4_data)
        print(
            f"V4 tools: {original_count} -> {filtered_count} tools ({original_count - filtered_count} removed)"
        )

        # Save filtered data
        save_json_file(v4_tools_file, filtered_v4_data)

    print("\nTool file filtering completed!")


if __name__ == "__main__":
    main()
