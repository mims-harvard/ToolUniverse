#!/usr/bin/env python3
"""
InsightLab end‑to‑end smoke test.

1. Provisions a Docker-hosted MCP LLM if Docker is available.
2. Uses the InsightLab LLM for hypothesis drafting.
3. Runs the harvest → test → register flow and calls the registered tool.
4. Summarises findings with the LLM.

Prerequisites:
  - Run this on a machine with Docker installed and outbound HTTPS access.
  - The image ghcr.io/tooluniverse/docker-llm-mcp:latest should be reachable (or already built).
"""

import json
import sys
import traceback
from pprint import pprint

import os
from pathlib import Path

# Ensure the repository's src directory is importable when running as a script
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from tooluniverse.execute_function import ToolUniverse  # noqa: E402


def pretty(title, payload):
    print(f"\n=== {title} ===")
    try:
        print(json.dumps(payload, indent=2))
    except TypeError:
        pprint(payload)


def main():
    tu = ToolUniverse()

    try:
        tu.load_tools()
    except Exception:
        print("Failed to load tools:")
        traceback.print_exc()
        return 1

    print("Tools loaded.")

    # 1. Provision Docker LLM
    try:
        provision = tu.run_one_function(
            {
                "name": "DockerLLMProvisioner",
                "arguments": {
                    "docker_image": "ghcr.io/tooluniverse/docker-llm-mcp:latest",
                    "host_port": 9010,
                    "reuse_container": True,
                    "tool_name": "InsightLabLLM",
                },
            }
        )
        pretty("DockerLLMProvisioner result", provision)
        llm_tool_name = provision.get("tool_name") or "InsightLabLLM"
    except Exception:
        print("Docker provision step failed (Docker must be available).")
        traceback.print_exc()
        return 1

    # Refresh tools to ensure local MCP client is loaded
    tu.load_tools()

    # 2. Draft a hypothesis with the local LLM
    hypothesis_prompt = (
        "Draft a research hypothesis about the linkage between vitamin D deficiency "
        "and autoimmune disorders. Provide two key questions to investigate."
    )
    try:
        hypothesis = tu.run_one_function(
            {
                "name": llm_tool_name,
                "arguments": {
                    "prompt": hypothesis_prompt,
                    "temperature": 0.3,
                    "max_tokens": 300,
                },
            }
        )
        pretty("Hypothesis output", hypothesis)
    except Exception:
        print("InsightLabLLM call failed.")
        traceback.print_exc()
        return 1

    # 3. Harvest → register a dataset API
    try:
        harvest = tu.run_one_function(
            {
                "name": "HarvestAutoRegistrar",
                "arguments": {
                    "query": "vitamin D immune dataset",
                    "limit": 5,
                    "tool_name": "vitamin_d_immune_api",
                    "auto_run": False,
                },
            }
        )
        pretty("HarvestAutoRegistrar result", harvest)
    except Exception:
        print("Harvest auto-registration failed (network required).")
        traceback.print_exc()
        return 1

    registered_name = harvest.get("registered_tool_name")
    if not registered_name:
        print("No tool was registered; check the attempts above.")
        return 1

    tu.load_tools()

    # Call the newly registered tool with sample arguments (may need adjusting)
    try:
        api_call = tu.run_one_function(
            {"name": registered_name, "arguments": {"q": "vitamin D", "rows": 5}}
        )
        pretty(f"Call to {registered_name}", api_call)
    except Exception:
        print(f"Call to {registered_name} failed.")
        traceback.print_exc()
        return 1

    # 4. Summarise the results with the LLM
    summary_prompt = f"""
    You produced the hypothesis:
    {hypothesis}

    And retrieved data from {registered_name}:
    {api_call}

    Provide:
      - 150-word summary
      - Confidence level between 0 and 1 with explanation
      - Two suggested follow-up experiments
    """
    try:
        summary = tu.run_one_function(
            {
                "name": llm_tool_name,
                "arguments": {
                    "prompt": summary_prompt,
                    "temperature": 0.3,
                    "max_tokens": 400,
                },
            }
        )
        pretty("InsightLab summary", summary)
    except Exception:
        print("Final summarisation failed.")
        traceback.print_exc()
        return 1

    print("\nInsightLab smoke test completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
