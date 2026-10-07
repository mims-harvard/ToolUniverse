"""Isolated CLI invocation and observed tool calls for the LAB-Bench ablation."""

import json
import os
import subprocess
import tempfile
import tomllib
from pathlib import Path


class AgentExecutionError(RuntimeError):
    """A broken invocation must not become a plausible benchmark score."""


def load_codex_config(path):
    with Path(path).open("rb") as handle:
        return tomllib.load(handle)


def validate_codex_pair(with_path, without_path):
    with_config = load_codex_config(with_path)
    without_config = load_codex_config(without_path)
    servers = with_config.get("mcp_servers", {})
    if set(servers) != {"tooluniverse"} or without_config.get("mcp_servers"):
        raise ValueError(
            "Only the with-condition may configure the ToolUniverse MCP server"
        )
    if not with_config.get("model"):
        raise ValueError("Pin the model in both Codex configurations")
    common_with = {k: v for k, v in with_config.items() if k != "mcp_servers"}
    common_without = {k: v for k, v in without_config.items() if k != "mcp_servers"}
    if common_with != common_without:
        raise ValueError(
            "Codex configurations must differ only in ToolUniverse presence"
        )


def codex_overrides(config, prefix=""):
    """Codex --config accepts key=value, not the path of a TOML file."""
    arguments = []
    for key, value in config.items():
        name = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            arguments.extend(codex_overrides(value, name))
        else:
            arguments.extend(["--config", f"{name}={json.dumps(value)}"])
    return arguments


def execute(command, prompt, timeout, env=None):
    # Each question starts in an empty workspace, including the baseline. Repository
    # instructions, old answers and project MCP settings cannot leak across conditions.
    with tempfile.TemporaryDirectory(prefix="tu-labbench-") as workdir:
        try:
            result = subprocess.run(
                command,
                input=prompt,
                capture_output=True,
                text=True,
                env=env,
                cwd=workdir,
                timeout=timeout,
            )
        except (subprocess.TimeoutExpired, OSError) as error:
            raise AgentExecutionError(f"Agent invocation failed: {error}") from error
    events = []
    for line in (result.stdout or "").splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    if not events:
        raise AgentExecutionError(
            "CLI produced no JSON events; check its version and options"
        )
    return result, events


def claude(prompt, with_tooluniverse, args):
    command = [
        args.claude_bin,
        "--print",
        "--verbose",
        "--output-format",
        "stream-json",
        "--model",
        args.model,
        "--max-turns",
        str(args.max_turns),
        "--setting-sources",
        "",
        "--strict-mcp-config",
    ]
    if with_tooluniverse:
        if not args.plugin_dir:
            raise ValueError("--plugin-dir is required for the with-condition")
        plugin = Path(args.plugin_dir).resolve()
        mcp = plugin / ".mcp.json"
        if not mcp.is_file():
            raise ValueError(f"Built plugin MCP configuration is missing: {mcp}")
        command.extend(["--plugin-dir", str(plugin), "--mcp-config", str(mcp)])
    else:
        command.extend(["--mcp-config", '{"mcpServers":{}}'])
    env = dict(os.environ)
    env.setdefault("MCP_TIMEOUT", "600000")
    env.setdefault("MCP_TOOL_TIMEOUT", "600000")
    result, events = execute(command, prompt, args.timeout, env)
    calls = {}
    answer = None
    for event in events:
        for block in event.get("message", {}).get("content", []):
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                calls[block["id"]] = {
                    "name": block.get("name", ""),
                    "arguments": block.get("input", {}),
                }
            elif (
                block.get("type") == "tool_result" and block.get("tool_use_id") in calls
            ):
                calls[block["tool_use_id"]].update(
                    result=block.get("content"),
                    completed=not block.get("is_error", False),
                )
        if event.get("type") == "result":
            if event.get("is_error"):
                raise AgentExecutionError(
                    f"Claude run failed: {event.get('subtype', 'unknown error')}"
                )
            answer = event.get("result")
    if result.returncode or not isinstance(answer, str):
        raise AgentExecutionError(
            "Claude did not complete successfully; do not score this run"
        )
    args.tool_calls = list(calls.values())
    return answer


def codex(prompt, with_tooluniverse, args):
    path = args.codex_with if with_tooluniverse else args.codex_without
    if not path:
        raise ValueError("--codex-with and --codex-without are required")
    config = load_codex_config(path)
    command = [
        args.codex_bin,
        "exec",
        "--ignore-user-config",
        "--ephemeral",
        "--skip-git-repo-check",
        "--json",
    ]
    command.extend(codex_overrides(config))
    command.append("-")
    result, events = execute(command, prompt, args.timeout)
    answer = None
    calls = []
    for event in events:
        if event.get("type") in {"error", "turn.failed"}:
            raise AgentExecutionError(
                "Codex reported a failed turn; do not score this run"
            )
        item = event.get("item", {})
        if event.get("type") != "item.completed":
            continue
        if item.get("type") == "agent_message":
            answer = item.get("text")
        elif item.get("type") == "mcp_tool_call":
            calls.append(
                {
                    "name": f"mcp__{item.get('server')}__{item.get('tool')}",
                    "arguments": item.get("arguments", {}),
                    "result": item.get("result"),
                    "completed": item.get("status") == "completed"
                    and not item.get("error"),
                }
            )
    if result.returncode or not isinstance(answer, str):
        raise AgentExecutionError(
            "Codex did not complete successfully; do not score this run"
        )
    args.tool_calls = calls
    return answer
