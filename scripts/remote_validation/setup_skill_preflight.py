#!/usr/bin/env python3
"""Preflight one or all documented ToolUniverse remote-tool deployments.

The static checks use only the Python standard library, so an operator can run
them before installing a remote tool's large scientific dependency stack.  The
optional live check imports FastMCP and verifies exact tool discovery, but it
does not invoke models or provider operations.
"""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_ROOT = REPO_ROOT / "skills"


@dataclass(frozen=True)
class Deployment:
    slug: str
    port: int
    operations: tuple[str, ...]
    required_env: tuple[str, ...] = ()
    required_commands: tuple[str, ...] = ()
    path_env: tuple[str, ...] = ()
    secret_env: tuple[str, ...] = ()

    @property
    def endpoint(self) -> str:
        return f"http://127.0.0.1:{self.port}/mcp"


DEPLOYMENTS = (
    Deployment(
        "boltz",
        8080,
        ("boltz2_docking",),
        required_commands=("boltz",),
    ),
    Deployment("borzoi", 8012, ("run_borzoi_predict", "run_borzoi_variant_effect")),
    Deployment(
        "cell2location",
        8019,
        ("run_cell2location_deconvolution",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
        path_env=("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
    ),
    Deployment(
        "cellrank",
        8028,
        ("run_cellrank_fate",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
        path_env=("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
    ),
    Deployment(
        "celltypist",
        8014,
        ("run_celltypist_annotate",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT", "CELLTYPIST_SAFE_MODEL_DIR"),
        path_env=("TOOLUNIVERSE_REMOTE_DATA_ROOT", "CELLTYPIST_SAFE_MODEL_DIR"),
    ),
    Deployment(
        "chrombpnet",
        8032,
        ("run_chrombpnet_predict", "run_chrombpnet_variant_effect"),
        ("CHROMBPNET_MODEL_PATH",),
        path_env=("CHROMBPNET_MODEL_PATH",),
    ),
    Deployment(
        "depmap-24q2",
        7002,
        ("compute_depmap24q2_gene_correlations",),
        ("DEPMAP_DATA_PATH",),
        path_env=("DEPMAP_DATA_PATH",),
    ),
    Deployment(
        "enformer", 8011, ("run_enformer_predict", "run_enformer_variant_effect")
    ),
    Deployment("esm", 8008, ("esm_embed_sequence",)),
    Deployment(
        "expert-feedback",
        9876,
        (
            "consult_human_expert",
            "get_expert_response",
            "list_pending_expert_requests",
            "submit_expert_response",
            "get_expert_status",
        ),
    ),
    Deployment(
        "harmony",
        8026,
        ("run_harmony_integrate",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
        path_env=("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
    ),
    Deployment(
        "immune-compass",
        7003,
        ("run_compass_prediction",),
        ("COMPASS_SAFE_MODEL_DIR",),
        path_env=("COMPASS_SAFE_MODEL_DIR",),
    ),
    Deployment(
        "ldsc",
        8013,
        ("run_ldsc_heritability", "run_ldsc_genetic_correlation"),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT", "LDSC_DIR", "LDSC_REF_DIR"),
        path_env=("TOOLUNIVERSE_REMOTE_DATA_ROOT", "LDSC_DIR", "LDSC_REF_DIR"),
    ),
    Deployment(
        "liana",
        8017,
        ("run_liana_cellphonedb",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
        path_env=("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
    ),
    Deployment(
        "macs3",
        8021,
        ("run_macs3_callpeak",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
        path_env=("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
    ),
    Deployment(
        "milo",
        8023,
        ("run_milo_differential_abundance",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
        path_env=("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
    ),
    Deployment("mofa", 8024, ("run_mofa_factors",)),
    Deployment(
        "monocle3",
        8031,
        ("run_monocle3_pseudotime",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
        ("Rscript",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
    ),
    Deployment(
        "paga",
        8022,
        ("run_paga_trajectory",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
        path_env=("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
    ),
    Deployment(
        "pinnacle",
        7001,
        ("run_pinnacle_ppi_retrieval",),
        ("PINNACLE_DATA_PATH",),
        path_env=("PINNACLE_DATA_PATH",),
    ),
    Deployment(
        "scanvi",
        8027,
        ("run_scanvi_annotate",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
        path_env=("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
    ),
    Deployment(
        "scrublet",
        8015,
        ("run_scrublet_doublets",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
        path_env=("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
    ),
    Deployment(
        "scvelo",
        8025,
        ("run_scvelo_velocity",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
        path_env=("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
    ),
    Deployment(
        "scvi",
        8010,
        ("run_scvi_integration", "run_scvi_differential_expression"),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
        path_env=("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
    ),
    Deployment(
        "singler",
        8029,
        ("run_singler_annotate",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
        ("Rscript",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
    ),
    Deployment(
        "slingshot",
        8030,
        ("run_slingshot_trajectory",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
        ("Rscript",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
    ),
    Deployment(
        "squidpy",
        8016,
        ("run_squidpy_nhood_enrichment",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
        path_env=("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
    ),
    Deployment(
        "tangram",
        8018,
        ("run_tangram_deconvolution",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
        path_env=("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
    ),
    Deployment(
        "transcriptformer",
        7000,
        ("run_transcriptformer_embedding_retrieval",),
        ("TRANSCRIPTFORMER_DATA_PATH",),
        path_env=("TRANSCRIPTFORMER_DATA_PATH",),
    ),
    Deployment(
        "uspto-downloader",
        8081,
        (
            "get_abstract_from_patent_app_number",
            "get_claims_from_patent_app_number",
            "get_full_text_from_patent_app_number",
        ),
        ("USPTO_API_KEY",),
        secret_env=("USPTO_API_KEY",),
    ),
)

BY_SLUG = {deployment.slug: deployment for deployment in DEPLOYMENTS}


def _skill_contract(deployment: Deployment) -> dict[str, Any]:
    skill_path = SKILLS_ROOT / f"setup-{deployment.slug}-remote-tool" / "SKILL.md"
    result: dict[str, Any] = {
        "ok": True,
        "skill": str(skill_path.relative_to(REPO_ROOT)),
    }
    if not skill_path.is_file():
        result.update(ok=False, error="setup skill is missing")
        return result

    text = skill_path.read_text(encoding="utf-8")
    module_match = re.search(
        r"^python -m (tooluniverse\.remote\.\S+)", text, re.MULTILINE
    )
    endpoint_match = re.search(r"endpoint is http://127\.0\.0\.1:(\d+)/mcp", text)
    if module_match is None or endpoint_match is None:
        result.update(ok=False, error="documented module or endpoint is missing")
        return result

    module = module_match.group(1)
    documented_port = int(endpoint_match.group(1))
    module_path = REPO_ROOT / "src" / Path(*module.split(".")).with_suffix(".py")
    representative_operations = tuple(
        re.findall(r"^Operation: (\S+)", text, re.MULTILINE)
    )
    requirements = re.findall(r"^python -m pip install -r (\S+)", text, re.MULTILINE)
    missing_requirements = [
        path for path in requirements if not (REPO_ROOT / path).is_file()
    ]
    problems = []
    if documented_port != deployment.port:
        problems.append(
            f"documented port {documented_port} != catalog port {deployment.port}"
        )
    if not module_path.is_file():
        problems.append(
            f"module source is missing: {module_path.relative_to(REPO_ROOT)}"
        )
    if not representative_operations:
        problems.append("representative operation is missing")
    elif not set(representative_operations).issubset(deployment.operations):
        problems.append("representative operation is absent from the expected tool set")
    if missing_requirements:
        problems.append(f"missing requirement files: {missing_requirements}")
    if "setup_skill_preflight.py" not in text:
        problems.append("shared preflight command is missing from the setup skill")
    if "tu remote login" not in text:
        problems.append("one-time remote login command is missing")
    if "tu remote logout" not in text:
        problems.append("remote logout recovery command is missing")
    if "expired, or revoked" not in text:
        problems.append("invalid-key recovery guidance is missing")
    one_command = f"tu remote share {deployment.slug}"
    if one_command not in text:
        problems.append(f"reviewed short share command is missing: {one_command}")

    result.update(
        ok=not problems,
        module=module,
        module_source=str(module_path.relative_to(REPO_ROOT)),
        endpoint=deployment.endpoint,
        expected_operations=list(deployment.operations),
        representative_operations=list(representative_operations),
        requirements=requirements,
        problems=problems,
    )
    return result


def _provider_environment(deployment: Deployment) -> dict[str, Any]:
    variables = []
    for name in deployment.required_env:
        value = os.getenv(name, "")
        item: dict[str, Any] = {"name": name, "set": bool(value)}
        if name in deployment.path_env:
            item["path_exists"] = bool(value) and Path(value).expanduser().exists()
        if name in deployment.secret_env:
            item["secret"] = True
        variables.append(item)

    commands = []
    for name in deployment.required_commands:
        override_name = "RSCRIPT_BIN" if name == "Rscript" else None
        override = os.getenv(override_name, "") if override_name else ""
        available = (
            Path(override).expanduser().is_file()
            if override
            else shutil.which(name) is not None
        )
        commands.append(
            {
                "name": name,
                "available": available,
                "override_environment": override_name,
                "override_set": bool(override),
            }
        )
    ok = all(item["set"] for item in variables)
    ok = ok and all(item.get("path_exists", True) for item in variables)
    ok = ok and all(item["available"] for item in commands)
    return {"ok": ok, "variables": variables, "commands": commands}


def _connect_prerequisites() -> dict[str, Any]:
    sdk_available = importlib.util.find_spec("tuplatform_connect") is not None
    key_available = bool(os.getenv("TOOLUNIVERSE_SERVICE_KEY", "").strip())
    return {
        "ok": sdk_available and key_available,
        "sdk_available": sdk_available,
        "service_key_set": key_available,
        "service_key_value_disclosed": False,
        "install_source": ("private pinned GitHub SSH source; not published on PyPI"),
        "installation_requires_authorized_github_read_access": True,
        "installation_requires_configured_ssh_key": True,
    }


async def _live_discovery(
    deployment: Deployment, endpoint: str, timeout: float
) -> dict[str, Any]:
    try:
        from fastmcp import Client
    except ImportError:
        return {
            "ok": False,
            "endpoint": endpoint,
            "error": "fastmcp is not installed in this environment",
        }

    try:
        async with asyncio.timeout(timeout):
            async with Client(endpoint) as client:
                discovered = sorted(tool.name for tool in await client.list_tools())
    except Exception as exc:  # noqa: BLE001 - preserve one failed endpoint in evidence
        return {
            "ok": False,
            "endpoint": endpoint,
            "error": f"{type(exc).__name__}: {exc}",
        }
    expected = sorted(deployment.operations)
    return {
        "ok": discovered == expected,
        "endpoint": endpoint,
        "expected_operations": expected,
        "discovered_operations": discovered,
        "discovery_only": True,
    }


async def _run(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    selected = list(DEPLOYMENTS) if args.all else [BY_SLUG[args.implementation]]
    checks = []
    python_supported = sys.version_info[:2] == (3, 12)
    failed = not python_supported
    for deployment in selected:
        item: dict[str, Any] = {
            "implementation": deployment.slug,
            "contract": _skill_contract(deployment),
        }
        failed = failed or not item["contract"]["ok"]
        if args.check_provider_env:
            item["provider_environment"] = _provider_environment(deployment)
            failed = failed or not item["provider_environment"]["ok"]
        checks.append(item)

    if args.live:
        live_results = await asyncio.gather(
            *(
                _live_discovery(
                    deployment,
                    args.url if args.url else deployment.endpoint,
                    args.timeout,
                )
                for deployment in selected
            )
        )
        for item, live_result in zip(checks, live_results, strict=True):
            item["live"] = live_result
            failed = failed or not live_result["ok"]

    connect = None
    if args.check_connect_prereqs:
        connect = _connect_prerequisites()
        failed = failed or not connect["ok"]

    result = {
        "ok": not failed,
        "scope": "all" if args.all else args.implementation,
        "python": {
            "version": ".".join(str(part) for part in sys.version_info[:3]),
            "supported_3_12": python_supported,
            "virtual_environment_active": sys.prefix != sys.base_prefix,
        },
        "checks": checks,
        "connect_prerequisites": connect,
        "claims": {
            "live_mode_invokes_models": False,
            "live_mode_validates_discovery_only": bool(args.live),
            "provider_env_mode_validates_artifact_contents_or_provenance": False,
            "connect_prerequisite_mode_authenticates_to_platform": False,
        },
    }
    return result, int(failed)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check documented remote-tool setup and optional live discovery."
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--implementation", choices=sorted(BY_SLUG))
    target.add_argument("--all", action="store_true")
    parser.add_argument(
        "--check-provider-env",
        action="store_true",
        help="require provider paths, credentials, and external runtimes",
    )
    parser.add_argument(
        "--check-connect-prereqs",
        action="store_true",
        help="require the relay SDK and a service key without printing its value",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="verify exact MCP tool discovery without invoking operations",
    )
    parser.add_argument(
        "--url",
        help="override the MCP endpoint for one implementation",
    )
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.url and args.all:
        parser.error("--url can only be used with one --implementation")
    if args.url and not args.live:
        parser.error("--url requires --live")

    result, exit_code = asyncio.run(_run(args))
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(
            json.dumps(
                {
                    "ok": result["ok"],
                    "output": str(args.output),
                    "scope": result["scope"],
                },
                sort_keys=True,
            )
        )
    else:
        print(rendered, end="")
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
