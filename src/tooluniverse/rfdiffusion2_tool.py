from __future__ import annotations

import os
import shlex
import subprocess
from typing import Any, Dict, List, Optional

from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("RFDiffusion2Tool")
class RFDiffusion2Tool(BaseTool):
    """Command-backed RFdiffusion2 protein backbone design tool."""

    DEFAULT_COMMAND = "run_inference.py"

    def run(self, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        arguments = arguments or {}
        validation_error = self.validate_parameters(arguments)
        if validation_error:
            return {"status": "error", "error": str(validation_error)}

        try:
            command_args = self._build_command(arguments)
        except ValueError as exc:
            return {"status": "error", "error": str(exc)}

        dry_run = bool(arguments.get("dry_run", False))
        if dry_run:
            return {
                "status": "success",
                "data": {
                    "dry_run": True,
                    "command": command_args,
                    "cwd": self._resolve_workdir(),
                },
            }

        configured_command = self._resolve_command()
        if not configured_command:
            return {
                "status": "error",
                "error": (
                    "RFDIFFUSION2_COMMAND is not set. Configure it on the "
                    "RFdiffusion2 server or call with dry_run=true."
                ),
            }

        timeout = int(arguments.get("timeout_seconds", 3600))
        try:
            completed = subprocess.run(
                command_args,
                cwd=self._resolve_workdir(),
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return {
                "status": "error",
                "error": f"RFdiffusion2 timed out after {timeout} seconds",
                "stdout": exc.stdout,
                "stderr": exc.stderr,
            }
        except OSError as exc:
            return {"status": "error", "error": f"Failed to run RFdiffusion2: {exc}"}

        status = "success" if completed.returncode == 0 else "error"
        data = {
            "returncode": completed.returncode,
            "command": command_args,
            "cwd": self._resolve_workdir(),
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "output_prefix": arguments.get("output_prefix"),
        }
        if status == "error":
            return {
                "status": "error",
                "error": "RFdiffusion2 command failed",
                "data": data,
            }
        return {"status": "success", "data": data}

    def _resolve_command(self) -> Optional[str]:
        return self.tool_config.get("command") or os.getenv("RFDIFFUSION2_COMMAND")

    def _resolve_workdir(self) -> Optional[str]:
        return self.tool_config.get("workdir") or os.getenv("RFDIFFUSION2_WORKDIR")

    def _base_command(self, dry_run: bool) -> List[str]:
        command = self._resolve_command()
        if not command and dry_run:
            command = self.DEFAULT_COMMAND
        if not command:
            return []
        return shlex.split(command)

    def _build_command(self, arguments: Dict[str, Any]) -> List[str]:
        command_args = self._base_command(bool(arguments.get("dry_run", False)))
        if not command_args:
            return []

        contig_map = arguments.get("contig_map")
        if isinstance(contig_map, list):
            if not all(isinstance(item, str) and item for item in contig_map):
                raise ValueError("contig_map list entries must be non-empty strings")
            contig_value = ",".join(contig_map)
        elif isinstance(contig_map, str) and contig_map:
            contig_value = contig_map
        else:
            raise ValueError("contig_map is required")

        command_args.append(f"contigmap.contigs=[{contig_value}]")

        mappings = {
            "input_pdb": "inference.input_pdb",
            "output_prefix": "inference.output_prefix",
            "num_designs": "inference.num_designs",
            "inference_steps": "diffuser.T",
        }
        for argument_name, hydra_name in mappings.items():
            if arguments.get(argument_name) is not None:
                command_args.append(f"{hydra_name}={arguments[argument_name]}")

        hotspot_residues = arguments.get("hotspot_residues")
        if hotspot_residues:
            if isinstance(hotspot_residues, str):
                hotspot_value = hotspot_residues
            elif isinstance(hotspot_residues, list) and all(
                isinstance(item, str) and item for item in hotspot_residues
            ):
                hotspot_value = ",".join(hotspot_residues)
            else:
                raise ValueError(
                    "hotspot_residues must be a string or list of non-empty strings"
                )
            command_args.append(f"ppi.hotspot_res=[{hotspot_value}]")

        extra_args = arguments.get("extra_args", [])
        if extra_args:
            if not isinstance(extra_args, list) or not all(
                isinstance(item, str) and item for item in extra_args
            ):
                raise ValueError("extra_args must be a list of non-empty strings")
            command_args.extend(extra_args)

        return command_args
