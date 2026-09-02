"""Safe foreground orchestration for provider-owned remote tools.

This module deliberately separates discovery from execution.  It can start a
reviewed provider module and relay its loopback MCP endpoint, but it never
downloads model artifacts, publishes a draft, or accepts caller-controlled
module names.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RemoteDeployment:
    """One reviewed remote-tool entry point."""

    slug: str
    module: str
    port: int
    operations: tuple[str, ...]
    required_env: tuple[str, ...] = ()
    path_env: tuple[str, ...] = ()
    required_commands: tuple[str, ...] = ()
    module_args: tuple[str, ...] = ()
    gpu_policy: str = "none"
    relay_workers: int = 1
    credential_probe: str = ""

    @property
    def endpoint(self) -> str:
        return f"http://127.0.0.1:{self.port}/mcp"


# Reviewed entry points shared by ``tu remote``.  Boltz was the GPU golden path
# used to validate this lifecycle before the catalog was expanded.
REMOTE_DEPLOYMENTS = (
    RemoteDeployment(
        slug="boltz",
        module="tooluniverse.remote.boltz.boltz_mcp_server",
        port=8080,
        operations=("boltz2_docking",),
        required_commands=("boltz",),
        gpu_policy="required",
    ),
    RemoteDeployment(
        "borzoi",
        "tooluniverse.remote.borzoi.borzoi_tool",
        8012,
        ("run_borzoi_predict", "run_borzoi_variant_effect"),
        gpu_policy="recommended",
    ),
    RemoteDeployment(
        "cell2location",
        "tooluniverse.remote.cell2location.cell2location_tool",
        8019,
        ("run_cell2location_deconvolution",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
        gpu_policy="recommended",
    ),
    RemoteDeployment(
        "cellrank",
        "tooluniverse.remote.cellrank.cellrank_tool",
        8028,
        ("run_cellrank_fate",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
    ),
    RemoteDeployment(
        "celltypist",
        "tooluniverse.remote.celltypist.celltypist_tool",
        8014,
        ("run_celltypist_annotate",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT", "CELLTYPIST_SAFE_MODEL_DIR"),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT", "CELLTYPIST_SAFE_MODEL_DIR"),
    ),
    RemoteDeployment(
        "chrombpnet",
        "tooluniverse.remote.chrombpnet.chrombpnet_tool",
        8032,
        ("run_chrombpnet_predict", "run_chrombpnet_variant_effect"),
        ("CHROMBPNET_MODEL_PATH",),
        ("CHROMBPNET_MODEL_PATH",),
        gpu_policy="recommended",
    ),
    RemoteDeployment(
        "depmap-24q2",
        "tooluniverse.remote.depmap_24q2.depmap_24q2_mcp_tool",
        7002,
        ("compute_depmap24q2_gene_correlations",),
        ("DEPMAP_DATA_PATH",),
        ("DEPMAP_DATA_PATH",),
    ),
    RemoteDeployment(
        "enformer",
        "tooluniverse.remote.enformer.enformer_tool",
        8011,
        ("run_enformer_predict", "run_enformer_variant_effect"),
        gpu_policy="recommended",
    ),
    RemoteDeployment(
        "esm",
        "tooluniverse.remote.esm.esm_tool",
        8008,
        ("esm_embed_sequence",),
        gpu_policy="recommended",
    ),
    RemoteDeployment(
        "expert-feedback",
        "tooluniverse.remote.expert_feedback.human_expert_mcp_tools",
        9876,
        (
            "consult_human_expert",
            "get_expert_response",
            "list_pending_expert_requests",
            "submit_expert_response",
            "get_expert_status",
        ),
        module_args=("--start-server",),
        relay_workers=2,
    ),
    RemoteDeployment(
        "harmony",
        "tooluniverse.remote.harmony.harmony_tool",
        8026,
        ("run_harmony_integrate",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
    ),
    RemoteDeployment(
        "immune-compass",
        "tooluniverse.remote.immune_compass.compass_tool",
        7003,
        ("run_compass_prediction",),
        ("COMPASS_SAFE_MODEL_DIR",),
        ("COMPASS_SAFE_MODEL_DIR",),
        gpu_policy="recommended",
    ),
    RemoteDeployment(
        "ldsc",
        "tooluniverse.remote.ldsc.ldsc_tool",
        8013,
        ("run_ldsc_heritability", "run_ldsc_genetic_correlation"),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT", "LDSC_DIR", "LDSC_REF_DIR"),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT", "LDSC_DIR", "LDSC_REF_DIR"),
    ),
    RemoteDeployment(
        "liana",
        "tooluniverse.remote.liana.liana_tool",
        8017,
        ("run_liana_cellphonedb",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
    ),
    RemoteDeployment(
        "macs3",
        "tooluniverse.remote.macs3.macs3_tool",
        8021,
        ("run_macs3_callpeak",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
    ),
    RemoteDeployment(
        "milo",
        "tooluniverse.remote.milo.milo_tool",
        8023,
        ("run_milo_differential_abundance",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
    ),
    RemoteDeployment(
        "mofa",
        "tooluniverse.remote.mofa.mofa_tool",
        8024,
        ("run_mofa_factors",),
    ),
    RemoteDeployment(
        "monocle3",
        "tooluniverse.remote.monocle3.monocle3_tool",
        8031,
        ("run_monocle3_pseudotime",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
        ("Rscript",),
    ),
    RemoteDeployment(
        "paga",
        "tooluniverse.remote.paga.paga_tool",
        8022,
        ("run_paga_trajectory",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
    ),
    RemoteDeployment(
        "pinnacle",
        "tooluniverse.remote.pinnacle.pinnacle_tool",
        7001,
        ("run_pinnacle_ppi_retrieval",),
        ("PINNACLE_DATA_PATH",),
        ("PINNACLE_DATA_PATH",),
    ),
    RemoteDeployment(
        "scanvi",
        "tooluniverse.remote.scanvi.scanvi_tool",
        8027,
        ("run_scanvi_annotate",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
        gpu_policy="recommended",
    ),
    RemoteDeployment(
        "scrublet",
        "tooluniverse.remote.scrublet.scrublet_tool",
        8015,
        ("run_scrublet_doublets",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
    ),
    RemoteDeployment(
        "scvelo",
        "tooluniverse.remote.scvelo.scvelo_tool",
        8025,
        ("run_scvelo_velocity",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
    ),
    RemoteDeployment(
        "scvi",
        "tooluniverse.remote.scvi.scvi_tool",
        8010,
        ("run_scvi_integration", "run_scvi_differential_expression"),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
        gpu_policy="recommended",
    ),
    RemoteDeployment(
        "singler",
        "tooluniverse.remote.singler.singler_tool",
        8029,
        ("run_singler_annotate",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
        ("Rscript",),
    ),
    RemoteDeployment(
        "slingshot",
        "tooluniverse.remote.slingshot.slingshot_tool",
        8030,
        ("run_slingshot_trajectory",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
        ("Rscript",),
    ),
    RemoteDeployment(
        "squidpy",
        "tooluniverse.remote.squidpy.squidpy_tool",
        8016,
        ("run_squidpy_nhood_enrichment",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
    ),
    RemoteDeployment(
        "tangram",
        "tooluniverse.remote.tangram.tangram_tool",
        8018,
        ("run_tangram_deconvolution",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
        ("TOOLUNIVERSE_REMOTE_DATA_ROOT",),
        gpu_policy="recommended",
    ),
    RemoteDeployment(
        "transcriptformer",
        "tooluniverse.remote.transcriptformer.transcriptformer_tool",
        7000,
        ("run_transcriptformer_embedding_retrieval",),
        ("TRANSCRIPTFORMER_DATA_PATH",),
        ("TRANSCRIPTFORMER_DATA_PATH",),
    ),
    RemoteDeployment(
        "uspto-downloader",
        "tooluniverse.remote.uspto_downloader.uspto_downloader_mcp_server",
        8081,
        (
            "get_abstract_from_patent_app_number",
            "get_claims_from_patent_app_number",
            "get_full_text_from_patent_app_number",
        ),
        ("USPTO_API_KEY",),
        credential_probe="uspto",
    ),
)

REMOTE_BY_SLUG = {deployment.slug: deployment for deployment in REMOTE_DEPLOYMENTS}


@dataclass
class ManagedRemoteProcess:
    """A provider subprocess owned by the current CLI invocation."""

    process: subprocess.Popen
    log_path: Path
    log_handle: Any


def resolve_python(
    value: str | None, deployment: RemoteDeployment | None = None
) -> str:
    """Resolve a provider Python without dereferencing its virtualenv symlink."""

    candidate = value
    if candidate is None and deployment is not None:
        variable = (
            "TOOLUNIVERSE_REMOTE_"
            + deployment.slug.upper().replace("-", "_")
            + "_PYTHON"
        )
        candidate = os.getenv(variable) or os.getenv("TOOLUNIVERSE_REMOTE_PYTHON")
        # Prefer the documented environment name.  ``<slug>-live`` is also a
        # supported local name because operators commonly keep a separately
        # validated runtime beside a build/provisioning environment.
        for environment_name in (deployment.slug, f"{deployment.slug}-live"):
            conventional = Path(".venvs") / environment_name / "bin" / "python"
            if candidate is None and conventional.is_file():
                candidate = str(conventional)
                break
    candidate = candidate or sys.executable
    resolved = shutil.which(candidate)
    if resolved is None:
        path = Path(candidate).expanduser()
        if path.is_file():
            resolved = str(path.resolve())
    if resolved is None:
        raise ValueError(f"provider Python was not found: {candidate}")
    # A venv's ``python`` is commonly a symlink to the base interpreter.  Using
    # Path.resolve() here silently drops the venv prefix, so packages and console
    # scripts installed only in the provider environment disappear.  Keep the
    # symlink path while still returning an absolute executable path.
    return os.path.abspath(os.path.expanduser(resolved))


def child_environment(python: str, deployment: RemoteDeployment) -> dict[str, str]:
    """Build a provider environment without copying secrets into arguments."""

    environment = os.environ.copy()
    # Platform credentials belong to the relay process, never to scientific
    # provider code. Provider-specific credentials (for example USPTO_API_KEY)
    # remain available because their reviewed deployment explicitly needs them.
    environment.pop("TOOLUNIVERSE_SERVICE_KEY", None)
    environment.pop("TU_SERVICE_KEY", None)
    python_bin = str(Path(python).parent)
    current_path = environment.get("PATH", "")
    environment["PATH"] = (
        python_bin if not current_path else python_bin + os.pathsep + current_path
    )
    environment["PYTHONUNBUFFERED"] = "1"
    environment["TOOLUNIVERSE_MCP_HOST"] = "127.0.0.1"
    environment["TOOLUNIVERSE_MCP_PORT"] = str(deployment.port)
    return environment


def _provider_probe_code(deployment: RemoteDeployment) -> str:
    module = json.dumps(deployment.module)
    commands = json.dumps(list(deployment.required_commands))
    check_gpu = repr(deployment.gpu_policy != "none")
    return f"""
import importlib.util, json, pathlib, shutil, sys

def module_exists_without_import(name):
    parts = name.split(".")
    spec = importlib.util.find_spec(parts[0])
    if spec is None:
        return False
    if len(parts) == 1:
        return True
    locations = list(spec.submodule_search_locations or [])
    for index, part in enumerate(parts[1:], start=1):
        final = index == len(parts) - 1
        next_locations = []
        for location in locations:
            base = pathlib.Path(location)
            if final and (base / (part + ".py")).is_file():
                return True
            package = base / part
            if package.is_dir():
                next_locations.append(str(package))
        locations = next_locations
        if not locations:
            return False
    return bool(locations)

result = {{
    "python_version": list(sys.version_info[:3]),
    "commands": {{name: shutil.which(name) is not None for name in {commands}}},
}}
try:
    result["module_available"] = module_exists_without_import({module})
except Exception as exc:
    result["module_available"] = False
    result["module_probe_error"] = type(exc).__name__
if {check_gpu}:
    gpu = {{"torch_available": False, "cuda_available": False}}
    try:
        import torch
        gpu["torch_available"] = True
        gpu["torch_version"] = str(torch.__version__)
        gpu["cuda_available"] = bool(torch.cuda.is_available())
        if gpu["cuda_available"]:
            gpu["device"] = str(torch.cuda.get_device_name(0))
            gpu["tensor_sum"] = float(torch.arange(8, device="cuda").sum().item())
    except Exception as exc:
        gpu["error"] = f"{{type(exc).__name__}}: {{exc}}"
    result["gpu"] = gpu
print(json.dumps(result, sort_keys=True))
"""


def _uspto_credential_status(key: str, timeout: float) -> int:
    """Return only the HTTP status from a bounded, non-redirecting key check."""

    from tooluniverse.platform_remote_tool import _NoRedirect

    query = urllib.parse.urlencode(
        {
            "q": "applicationMetaData.patentNumber:9022434",
            "limit": "1",
        }
    )
    request = urllib.request.Request(
        "https://api.uspto.gov/api/v1/patent/applications/search?" + query,
        headers={
            "X-API-KEY": key,
            "Accept": "application/json",
            "User-Agent": "tooluniverse-remote-preflight/1",
        },
    )
    try:
        with urllib.request.build_opener(_NoRedirect).open(
            request, timeout=max(1.0, min(timeout, 15.0))
        ) as response:
            return int(response.status)
    except urllib.error.HTTPError as exc:
        return int(exc.code)


def _check_provider_credentials(
    deployment: RemoteDeployment, *, timeout: float
) -> dict[str, Any] | None:
    """Verify credentials whose providers offer a safe, bounded readiness probe."""

    if deployment.credential_probe != "uspto":
        return None
    key = os.getenv("USPTO_API_KEY", "")
    if not key:
        return {
            "name": "USPTO_API_KEY",
            "checked": False,
            "ready": False,
            "detail": "missing; obtain or export a USPTO Open Data Portal key",
        }
    try:
        status = _uspto_credential_status(key, timeout)
    except (OSError, TimeoutError, urllib.error.URLError) as exc:
        return {
            "name": "USPTO_API_KEY",
            "checked": False,
            "ready": False,
            "detail": f"could not verify with USPTO ({type(exc).__name__})",
        }
    if status in {401, 403}:
        return {
            "name": "USPTO_API_KEY",
            "checked": True,
            "ready": False,
            "http_status": status,
            "detail": "USPTO rejected the key; renew or activate it before launch",
        }
    ready = 200 <= status < 300 or status == 404
    return {
        "name": "USPTO_API_KEY",
        "checked": True,
        "ready": ready,
        "http_status": status,
        "detail": (
            "USPTO accepted the provider credential"
            if ready
            else "USPTO credential readiness returned an unexpected status"
        ),
    }


def check_environment(
    deployment: RemoteDeployment,
    *,
    python: str | None = None,
    share: bool = False,
    service_key_available: bool | None = None,
    allow_cpu: bool = False,
    timeout: float = 30,
) -> dict[str, Any]:
    """Check a target provider environment without importing the model locally."""

    try:
        provider_python = resolve_python(python, deployment)
    except ValueError as exc:
        return {
            "ok": False,
            "implementation": deployment.slug,
            "error": str(exc),
            "secret_values_disclosed": False,
        }

    environment = child_environment(provider_python, deployment)
    try:
        completed = subprocess.run(
            [provider_python, "-c", _provider_probe_code(deployment)],
            env=environment,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "ok": False,
            "implementation": deployment.slug,
            "python": provider_python,
            "error": f"provider preflight failed: {type(exc).__name__}",
            "secret_values_disclosed": False,
        }

    # Some ML runtimes print notices to stdout during import.  The probe owns the
    # final line, so parse that bounded JSON record without exposing stderr.
    stdout_lines = completed.stdout.strip().splitlines()
    try:
        provider = json.loads(stdout_lines[-1] if stdout_lines else "")
    except (json.JSONDecodeError, TypeError):
        provider = {
            "error": "provider preflight returned invalid output",
            "exit_code": completed.returncode,
            "python_version": [],
            "module_available": None,
            "commands": {},
        }

    variables = []
    for name in deployment.required_env:
        value = os.getenv(name, "")
        item: dict[str, Any] = {"name": name, "set": bool(value)}
        if name in deployment.path_env:
            item["path_exists"] = bool(value) and Path(value).expanduser().exists()
        variables.append(item)

    python_version = provider.get("python_version") or []
    python_supported = (
        python_version[:2] == [3, 12] if len(python_version) >= 2 else None
    )
    module_available_value = provider.get("module_available")
    module_available = (
        module_available_value if isinstance(module_available_value, bool) else None
    )
    commands_ok = all((provider.get("commands") or {}).values())
    variables_ok = all(item["set"] for item in variables) and all(
        item.get("path_exists", True) for item in variables
    )
    credential_check = _check_provider_credentials(deployment, timeout=timeout)
    credentials_ok = credential_check is None or credential_check.get("ready") is True
    gpu = provider.get("gpu") or {}
    gpu_required = deployment.gpu_policy == "required" and not allow_cpu
    gpu_ok = not gpu_required or (
        gpu.get("cuda_available") is True and gpu.get("tensor_sum") == 28.0
    )

    sdk_available = importlib.util.find_spec("tuplatform_connect") is not None
    key_set = (
        bool(os.getenv("TOOLUNIVERSE_SERVICE_KEY", "").strip())
        if service_key_available is None
        else service_key_available
    )
    share_ok = not share or (sdk_available and key_set)
    ok = (
        completed.returncode == 0
        and python_supported is True
        and module_available is True
        and commands_ok
        and variables_ok
        and credentials_ok
        and gpu_ok
        and share_ok
    )
    return {
        "ok": ok,
        "implementation": deployment.slug,
        "python": provider_python,
        "python_supported_3_12": python_supported,
        "provider": provider,
        "provider_environment": variables,
        "provider_credentials": credential_check,
        "gpu_policy": deployment.gpu_policy,
        "cpu_override": allow_cpu,
        "share_prerequisites": {
            "requested": share,
            "sdk_available": sdk_available,
            "service_key_set": key_set,
        },
        "secret_values_disclosed": False,
    }


async def _discover_async(
    deployment: RemoteDeployment, endpoint: str, timeout: float
) -> dict[str, Any]:
    try:
        from fastmcp import Client
    except ImportError:
        return {
            "ok": False,
            "reachable": False,
            "endpoint": endpoint,
            "error": "fastmcp is not installed in the orchestration environment",
        }

    try:
        async with asyncio.timeout(timeout):
            async with Client(endpoint) as client:
                discovered = sorted(tool.name for tool in await client.list_tools())
    except Exception as exc:  # noqa: BLE001 - report one bounded probe failure
        return {
            "ok": False,
            "reachable": False,
            "endpoint": endpoint,
            "error": f"{type(exc).__name__}: {exc}",
        }
    expected = sorted(deployment.operations)
    return {
        "ok": discovered == expected,
        "reachable": True,
        "endpoint": endpoint,
        "expected_operations": expected,
        "discovered_operations": discovered,
    }


def discover_endpoint(
    deployment: RemoteDeployment, endpoint: str | None = None, timeout: float = 5
) -> dict[str, Any]:
    """Discover an exact local MCP tool set."""

    return asyncio.run(
        _discover_async(deployment, endpoint or deployment.endpoint, timeout)
    )


def start_provider(
    deployment: RemoteDeployment,
    *,
    python: str,
    log_dir: str | Path,
) -> ManagedRemoteProcess:
    """Start one reviewed provider module with output redirected to a log."""

    directory = Path(log_dir).expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    log_path = directory / f"{deployment.slug}.log"
    log_handle = log_path.open("a", encoding="utf-8")
    command = [python, "-m", deployment.module, *deployment.module_args]
    try:
        process = subprocess.Popen(
            command,
            env=child_environment(python, deployment),
            stdin=subprocess.DEVNULL,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            # Keep provider subprocesses (for example ``boltz predict``) in a
            # dedicated group so cancellation cannot orphan GPU work.
            start_new_session=True,
        )
    except Exception:
        log_handle.close()
        raise
    return ManagedRemoteProcess(process, log_path, log_handle)


def wait_until_ready(
    deployment: RemoteDeployment,
    managed: ManagedRemoteProcess,
    *,
    timeout: float,
) -> dict[str, Any]:
    """Wait for exact discovery or fail with a log location."""

    deadline = time.monotonic() + timeout
    last_result: dict[str, Any] = {}
    while time.monotonic() < deadline:
        exit_code = managed.process.poll()
        if exit_code is not None:
            raise RuntimeError(
                f"provider exited with code {exit_code}; inspect {managed.log_path}"
            )
        last_result = discover_endpoint(deployment, timeout=1)
        if last_result.get("reachable"):
            if not last_result.get("ok"):
                raise RuntimeError(
                    "local MCP tool set does not match the reviewed deployment contract"
                )
            return last_result
        time.sleep(0.2)
    raise RuntimeError(
        f"provider did not become ready within {timeout:g} seconds; "
        f"inspect {managed.log_path}; last probe: {last_result.get('error', 'unknown')}"
    )


def stop_provider(managed: ManagedRemoteProcess | None, timeout: float = 10) -> None:
    """Stop only the provider process created by this invocation."""

    if managed is None:
        return
    try:
        if managed.process.poll() is None:
            if os.name == "posix":
                try:
                    os.killpg(managed.process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            else:  # pragma: no cover - Windows fallback
                managed.process.terminate()
            try:
                managed.process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                if os.name == "posix":
                    try:
                        os.killpg(managed.process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                else:  # pragma: no cover - Windows fallback
                    managed.process.kill()
                managed.process.wait(timeout=timeout)
    finally:
        managed.log_handle.close()


def ensure_provider(
    deployment: RemoteDeployment,
    *,
    python: str,
    log_dir: str | Path,
    startup_timeout: float,
) -> tuple[ManagedRemoteProcess | None, dict[str, Any]]:
    """Reuse an exact endpoint or start a provider and validate it."""

    current = discover_endpoint(deployment, timeout=2)
    if current.get("reachable"):
        if not current.get("ok"):
            raise RuntimeError(
                f"port {deployment.port} is serving a different MCP tool set"
            )
        return None, current

    managed = start_provider(deployment, python=python, log_dir=log_dir)
    try:
        ready = wait_until_ready(deployment, managed, timeout=startup_timeout)
    except Exception:
        stop_provider(managed)
        raise
    return managed, ready
