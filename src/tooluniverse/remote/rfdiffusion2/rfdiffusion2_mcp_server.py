from __future__ import annotations

import json
import os
import sys

from fastmcp import FastMCP

from tooluniverse.rfdiffusion2_tool import RFDiffusion2Tool

try:
    with open(
        os.path.join(os.path.dirname(__file__), "rfdiffusion2_client_tools.json"),
        "r",
        encoding="utf-8",
    ) as f:
        rfdiffusion2_tools = json.load(f)
except FileNotFoundError as e:
    print(f"Error: {e}")
    print(f"Is rfdiffusion2_client_tools.json next to {__file__}?")
    sys.exit(1)

server = FastMCP("RFdiffusion2 MCP Server")
agents = {
    tool_config["name"]: RFDiffusion2Tool(tool_config=tool_config)
    for tool_config in rfdiffusion2_tools
}


@server.tool()
def run_rfdiffusion2(query: dict):
    """Run RFdiffusion2 protein backbone design.

    Args:
        query: RFdiffusion2 arguments such as contig_map, input_pdb,
            output_prefix, num_designs, hotspot_residues, extra_args, and dry_run.

    Returns:
        A ToolUniverse-style result dictionary with status, data, and error.
    """
    return agents["rfdiffusion2_design"].run(query)


if __name__ == "__main__":
    server.run(
        transport="streamable-http", host="0.0.0.0", port=8080, stateless_http=True
    )
