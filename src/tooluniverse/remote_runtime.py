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
from collections.abc import Iterable
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
        # The manifest's `[env] python` names this, and leaving it out of
        # required_env meant `tu remote check boltz` probed the SERVER's
        # interpreter and reported a GPU verdict about the wrong process.
        required_env=("TOOLUNIVERSE_BOLTZ_PYTHON",),
        path_env=("BOLTZ_CACHE",),
        required_commands=("boltz",),
        gpu_policy="required",
    ),
    RemoteDeployment(
        "evo2",
        "tooluniverse.remote.evo2.evo2_tool",
        8041,
        ("run_evo2_score", "run_evo2_embed"),
        ("EVO2_OPT_WEIGHTS", "TOOLUNIVERSE_EVO2_PYTHON"),
        ("EVO2_OPT_WEIGHTS",),
        gpu_policy="required",
    ),
    RemoteDeployment(
        "apnovo",
        "tooluniverse.remote.apnovo.apnovo_tool",
        8059,
        (
            "apnovo_validate_motif",
            "apnovo_generate_designs",
            "apnovo_resequence_designs",
            "apnovo_evaluate_designs",
        ),
        ("APNOVO_WEIGHTS_ROOT", "TOOLUNIVERSE_APNOVO_PYTHON"),
        ("APNOVO_WEIGHTS_ROOT",),
        gpu_policy="required",
    ),
    RemoteDeployment(
        "atlasfold",
        "tooluniverse.remote.atlasfold.atlasfold_tool",
        8043,
        ("atlasfold_predict",),
        ("TOOLUNIVERSE_ATLASFOLD_PYTHON",),
        (),
        gpu_policy="required",
    ),
    RemoteDeployment(
        "af2ig",
        "tooluniverse.remote.af2ig.af2ig_tool",
        8053,
        ("af2ig_predict",),
        ("TOOLUNIVERSE_AF2IG_PYTHON",),
        ("AF2_PARAMS", "AF2IG_DIR"),
        gpu_policy="required",
    ),
    RemoteDeployment(
        "af3_jax",
        "tooluniverse.remote.af3_jax.af3_jax_tool",
        8045,
        ("af3_jax_predict",),
        ("TOOLUNIVERSE_AF3_JAX_PYTHON", "AF3_JAX_REPO"),
        ("AF3_JAX_PARAMS_ROOT", "AF3_JAX_REPO"),
        gpu_policy="required",
    ),
    RemoteDeployment(
        "af3_torch",
        "tooluniverse.remote.af3_torch.af3_torch_tool",
        8036,
        ("af3_torch_predict",),
        ("TOOLUNIVERSE_AF3_TORCH_PYTHON", "AF3_TORCH_JAX_PY", "AF3_TORCH_JAX_REPO"),
        ("AF3_TORCH_PARAMS_DIR", "AF3_TORCH_JAX_REPO"),
        gpu_policy="required",
    ),
    RemoteDeployment(
        "boltzgen",
        "tooluniverse.remote.boltzgen.boltzgen_tool",
        8035,
        ("boltzgen_design",),
        ("BOLTZGEN_CACHE", "TOOLUNIVERSE_BOLTZGEN_PYTHON"),
        ("BOLTZGEN_CACHE",),
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
        "borzoi_calico",
        "tooluniverse.remote.borzoi_calico.borzoi_calico_tool",
        8061,
        ("run_borzoi_calico_sad",),
        (
            "TOOLUNIVERSE_BORZOI_CALICO_PYTHON",
            "BORZOI_DIR",
            "BASKERVILLE_DIR",
        ),
        ("BORZOI_CALICO_WEIGHTS",),
        # `policy = "none"`: TensorFlow publishes no GPU-capable aarch64 wheel at
        # any version, so this reserves no VRAM and is admitted while the card is
        # full. Not a replacement for `borzoi` above -- a different operation
        # (upstream's SAD statistics from coordinates, against pinned hg38).
        gpu_policy="none",
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
        "chai1",
        "tooluniverse.remote.chai1.chai1_tool",
        8033,
        ("chai1_fold",),
        ("CHAI_DOWNLOADS_DIR", "TOOLUNIVERSE_CHAI1_PYTHON"),
        ("CHAI_DOWNLOADS_DIR",),
        gpu_policy="required",
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
        "colabdesign",
        "tooluniverse.remote.colabdesign.colabdesign_tool",
        8054,
        ("colabdesign_design",),
        ("TOOLUNIVERSE_COLABDESIGN_PYTHON",),
        ("COLABDESIGN_PARAMS_DIR",),
        gpu_policy="required",
    ),
    RemoteDeployment(
        "colabfold",
        "tooluniverse.remote.colabfold.colabfold_tool",
        8051,
        ("colabfold_predict",),
        ("TOOLUNIVERSE_COLABFOLD_PYTHON",),
        ("COLABFOLD_OPT_DATA_DIR",),
        gpu_policy="required",
    ),
    RemoteDeployment(
        "complexa",
        "tooluniverse.remote.complexa.complexa_tool",
        8056,
        ("complexa_design_binder",),
        ("TOOLUNIVERSE_COMPLEXA_PYTHON",),
        (),
        gpu_policy="required",
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
        "ef2inv",
        "tooluniverse.remote.ef2inv.ef2inv_tool",
        8042,
        ("ef2inv_design",),
        ("HF_HOME", "TOOLUNIVERSE_EF2INV_PYTHON"),
        ("HF_HOME",),
        gpu_policy="required",
    ),
    RemoteDeployment(
        "enformer",
        "tooluniverse.remote.enformer.enformer_tool",
        8011,
        ("run_enformer_predict", "run_enformer_variant_effect"),
        ("TOOLUNIVERSE_ENFORMER_PYTHON",),
        ("HF_HOME",),
        gpu_policy="recommended",
    ),
    RemoteDeployment(
        "enformer_deepmind",
        "tooluniverse.remote.enformer_deepmind.enformer_deepmind_tool",
        8060,
        ("run_enformer_deepmind_predict",),
        ("TOOLUNIVERSE_ENFORMER_DEEPMIND_PYTHON",),
        ("TFHUB_CACHE_DIR",),
        # `policy = "none"`: the official release is TensorFlow, and TensorFlow
        # publishes no GPU-capable aarch64 wheel at any version, so this one
        # reserves no VRAM and is admitted while the card is full. It is the
        # complement of `enformer` above (the torch port, on the card), not its
        # replacement.
        gpu_policy="none",
    ),
    RemoteDeployment(
        "esm",
        "tooluniverse.remote.esm.esm_tool",
        8008,
        ("esm_embed_sequence",),
        gpu_policy="recommended",
    ),
    RemoteDeployment(
        "e1",
        "tooluniverse.remote.e1.e1_tool",
        8044,
        ("run_e1_score_variants", "run_e1_embed"),
        ("HF_HOME", "TOOLUNIVERSE_E1_PYTHON"),
        ("HF_HOME",),
        gpu_policy="required",
    ),
    RemoteDeployment(
        "esm_if1",
        "tooluniverse.remote.esm_if1.esm_if1_tool",
        8050,
        ("esm_if1_design",),
        ("TOOLUNIVERSE_ESM_IF1_PYTHON",),
        (),
        gpu_policy="none",
    ),
    RemoteDeployment(
        "esmc",
        "tooluniverse.remote.esmc.esmc_tool",
        8037,
        ("run_esmc_embed", "run_esmc_logits"),
        ("HF_HOME", "TOOLUNIVERSE_ESMC_PYTHON"),
        ("HF_HOME",),
        gpu_policy="required",
    ),
    RemoteDeployment(
        "esmfold2",
        "tooluniverse.remote.esmfold2.esmfold2_tool",
        8038,
        ("esmfold2_fold",),
        ("HF_HOME", "TOOLUNIVERSE_ESMFOLD2_PYTHON"),
        ("HF_HOME",),
        gpu_policy="required",
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
        "genie3",
        "tooluniverse.remote.genie3.genie3_tool",
        8048,
        ("genie3_design",),
        ("GENIE3_WEIGHTS", "TOOLUNIVERSE_GENIE3_PYTHON"),
        ("GENIE3_WEIGHTS",),
        gpu_policy="required",
    ),
    RemoteDeployment(
        "gpnstar",
        "tooluniverse.remote.gpnstar.gpnstar_tool",
        8057,
        ("run_gpnstar_vep",),
        ("HF_HOME", "TOOLUNIVERSE_GPNSTAR_PYTHON"),
        ("HF_HOME",),
        gpu_policy="required",
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
        "mosaic",
        "tooluniverse.remote.mosaic.mosaic_tool",
        8055,
        ("mosaic_design_binder",),
        ("TOOLUNIVERSE_MOSAIC_PYTHON",),
        ("MOSAIC_CACHE_DIR",),
        gpu_policy="required",
    ),
    RemoteDeployment(
        "opendde",
        "tooluniverse.remote.opendde.opendde_tool",
        8058,
        ("opendde_fold",),
        ("TOOLUNIVERSE_OPENDDE_PYTHON",),
        ("OPENDDE_ROOT_DIR",),
        gpu_policy="required",
    ),
    RemoteDeployment(
        "openfold3",
        "tooluniverse.remote.openfold3.openfold3_tool",
        8039,
        ("openfold3_fold",),
        ("TOOLUNIVERSE_OPENFOLD3_PYTHON",),
        (),
        gpu_policy="required",
    ),
    RemoteDeployment(
        "openfold3_ob0",
        "tooluniverse.remote.openfold3_ob0.openfold3_ob0_tool",
        8052,
        ("openfold3_ob0_fold",),
        ("TOOLUNIVERSE_OPENFOLD3_OB0_PYTHON",),
        (),
        gpu_policy="required",
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
        "progen2",
        "tooluniverse.remote.progen2.progen2_tool",
        8047,
        ("run_progen2_score", "run_progen2_generate"),
        ("PROGEN2_WEIGHTS", "TOOLUNIVERSE_PROGEN2_PYTHON"),
        ("PROGEN2_WEIGHTS",),
        gpu_policy="required",
    ),
    RemoteDeployment(
        "proteinmpnn",
        "tooluniverse.remote.proteinmpnn.proteinmpnn_tool",
        8049,
        ("proteinmpnn_design",),
        ("TOOLUNIVERSE_PROTEINMPNN_PYTHON",),
        ("TOOLUNIVERSE_PROTEINMPNN_WEIGHTS",),
        # `policy = "none"`: no card is required and none is used, which is why
        # this one can be resident while every other provider is.
        gpu_policy="none",
    ),
    RemoteDeployment(
        "protenix_v1",
        "tooluniverse.remote.protenix_v1.protenix_v1_tool",
        8046,
        ("protenix_v1_fold",),
        ("TOOLUNIVERSE_PROTENIX_V1_PYTHON",),
        (),
        gpu_policy="required",
    ),
    RemoteDeployment(
        "rfdiffusion3",
        "tooluniverse.remote.rfdiffusion3.rfdiffusion3_tool",
        8040,
        ("rfdiffusion3_design",),
        ("FOUNDRY_CHECKPOINT_DIRS", "TOOLUNIVERSE_RFDIFFUSION3_PYTHON"),
        ("FOUNDRY_CHECKPOINT_DIRS",),
        gpu_policy="required",
    ),
    RemoteDeployment(
        "rosettafold3",
        "tooluniverse.remote.rosettafold3.rosettafold3_tool",
        8034,
        ("rosettafold3_predict",),
        ("TOOLUNIVERSE_ROSETTAFOLD3_PYTHON",),
        (),
        gpu_policy="required",
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


# Variables a provider process needs to function at all, whatever it computes: where to
# find libraries and caches, how to reach the network, how to talk to a GPU. None of them
# is a credential by convention, which is what makes listing them safe.
#
# LD_PRELOAD is deliberately absent. No reviewed provider needs it and it is the standard
# way to get arbitrary code into someone else's process.
PROVIDER_ENV_BASE = frozenset(
    {
        # Without PATH the provider's own bin directory becomes its entire search path, so
        # every required_commands binary -- Rscript for the four R providers, boltz for its
        # own -- stops resolving. The existing runtime test caught exactly that.
        "PATH",
        "HOME",
        "USER",
        "LOGNAME",
        "SHELL",
        "LANG",
        "LANGUAGE",
        "TZ",
        "TMPDIR",
        "TEMP",
        "TMP",
        "LD_LIBRARY_PATH",
        "PYTHONPATH",
        "VIRTUAL_ENV",
        "CONDA_PREFIX",
        "CONDA_DEFAULT_ENV",
        "SSL_CERT_FILE",
        "SSL_CERT_DIR",
        "REQUESTS_CA_BUNDLE",
        "CURL_CA_BUNDLE",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "NO_PROXY",
        "http_proxy",
        "https_proxy",
        "no_proxy",
        "XDG_CACHE_HOME",
        "XDG_CONFIG_HOME",
        "XDG_DATA_HOME",
        "HF_HOME",
        "TORCH_HOME",
        "MPLCONFIGDIR",
        "NUMBA_CACHE_DIR",
    }
)

# Whole families whose names cannot hold a credential by convention: device selection,
# thread counts, BLAS tuning, R library paths.
#
# Not HF_: that family contains HF_TOKEN. HF_HOME is listed above by name instead, which is
# the difference between allowing a cache location and allowing an access token.
PROVIDER_ENV_PREFIXES = (
    "CUDA_",
    "NVIDIA_",
    "NCCL_",
    "OMP_",
    "MKL_",
    "OPENBLAS_",
    "NUMEXPR_",
    "LC_",
    "R_",
)


def provider_environment_names(
    deployment: RemoteDeployment, extra: Iterable[str] = ()
) -> set[str]:
    """Every variable this provider is allowed to see, by name."""

    allowed = set(PROVIDER_ENV_BASE)
    allowed |= set(deployment.required_env)
    allowed |= set(deployment.path_env)
    allowed |= {name for name in extra if name}
    allowed |= {name for name in os.environ if name.startswith(PROVIDER_ENV_PREFIXES)}
    return allowed



def explain_environment_failure(
    report: dict[str, Any], deployment: RemoteDeployment
) -> list[str]:
    """Turn a failed environment check into sentences with a fix in each one.

    The CLI used to print the exclusion reason from report["checks"], a key this function's
    report has never contained, so every provider was excluded with the words "environment
    check failed" and nothing else. The reason was computed and then thrown away.

    That matters most for the people this is aimed at. A biologist whose virtual environment
    is Python 3.11 cannot act on "environment check failed"; they can act on "needs Python
    3.12, this one is 3.11".

    Mirrors the conditions that make up report["ok"], in the order someone would fix them:
    nothing later is worth reporting while the interpreter itself is wrong.
    """
    slug = deployment.slug
    setup = f"The setup guide for it is skills/setup-{slug}-remote-tool."
    provider = report.get("provider") or {}
    reasons: list[str] = []

    if report.get("error"):
        return [str(report["error"])]

    if provider.get("error"):
        # The probe could not even report. Its exit code is the only honest detail; stderr is
        # deliberately not surfaced because a provider's output can carry credentials.
        reasons.append(
            f"{slug} could not be checked: {provider['error']}"
            f" (exit code {provider.get('exit_code', '?')}). {setup}"
        )
        return reasons

    if report.get("python_supported_3_12") is False:
        version = provider.get("python_version") or []
        running = ".".join(str(part) for part in version[:2]) if version else "something else"
        reasons.append(
            f"{slug} needs Python 3.12; this environment is {running}. Make one with "
            f"`python3.12 -m venv .venv` and install into it."
        )
        # An interpreter mismatch makes every later check meaningless: the packages are
        # missing because they were installed somewhere else.
        return reasons

    if provider.get("module_available") is False:
        reasons.append(
            f"{slug} is not installed in this environment. {setup}"
        )

    for name, present in (provider.get("commands") or {}).items():
        if not present:
            reasons.append(
                f"{slug} runs `{name}`, which is not on this machine's PATH. {setup}"
            )

    for item in report.get("provider_environment") or []:
        name = item.get("name", "a variable")
        if not item.get("set"):
            reasons.append(
                f"{slug} needs the environment variable {name}, which is not set."
            )
        elif not item.get("path_exists", True):
            reasons.append(
                f"{name} points at a path that does not exist on this machine."
            )

    credentials = report.get("provider_credentials")
    if isinstance(credentials, dict) and credentials.get("ready") is not True:
        detail = str(credentials.get("detail") or "it is not available")
        reasons.append(f"{slug} needs a credential and {detail}.")

    if report.get("gpu_policy") == "required" and not report.get("cpu_override"):
        gpu = provider.get("gpu") or {}
        if gpu.get("cuda_available") is not True:
            reasons.append(
                f"{slug} needs a CUDA GPU and this machine has none available. Add "
                f"--allow-cpu to run it on the processor instead, which is much slower."
            )
        elif gpu.get("tensor_sum") != 28.0:
            reasons.append(
                f"{slug} found a GPU but a test calculation on it gave the wrong answer, so "
                f"the CUDA installation is not working."
            )

    share = report.get("share_prerequisites") or {}
    if share.get("requested"):
        if not share.get("sdk_available"):
            reasons.append(
                "Sharing needs tuplatform-connect, which is not installed in this environment."
            )
        if not share.get("service_key_set"):
            reasons.append(
                "Sharing needs this computer to be signed in. Run `tu remote login`, or let "
                "the command open a browser for you."
            )

    if not reasons:
        # Everything checkable passed and the result still says no. Say that, rather than
        # inventing a cause, and name the command that prints the whole report.
        reasons.append(
            f"{slug} did not pass its environment check and the report gives no reason. "
            f"`tu remote check {slug}` prints all of it."
        )
    return reasons

def child_environment(
    python: str, deployment: RemoteDeployment, *, extra_env: Iterable[str] = ()
) -> dict[str, str]:
    """Build a provider environment from an allowlist rather than by inheritance.

    A provider used to receive a copy of the whole process environment with two platform
    keys removed. That is defensible when the machine only serves its owner, and wrong as
    soon as it serves anyone else: a reviewed provider would run under the owner's identity
    holding every unrelated credential in their shell -- cloud keys, model-provider keys,
    database URLs -- any of which a crash dump, a debug log, or an outbound request could
    carry somewhere the owner did not intend. It also meant a caller's work could silently
    spend the owner's paid API quota.

    So a provider now sees only what it declared it needs, plus the infrastructure
    variables every process needs. Anything a site requires beyond that is passed
    explicitly with ``--pass-env``, which keeps the decision with the operator instead of
    making it for them by copying everything.
    """

    allowed = provider_environment_names(deployment, extra_env)
    environment = {name: value for name, value in os.environ.items() if name in allowed}
    # Kept out regardless: these authenticate this machine to the platform, and nothing a
    # provider computes has any business holding them.
    for platform_key in ("TOOLUNIVERSE_SERVICE_KEY", "TU_SERVICE_KEY"):
        environment.pop(platform_key, None)
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
    if not gpu["cuda_available"]:
        # ASK EVERY FRAMEWORK, NOT TORCH. A provider may hold the card with JAX
        # and carry a CPU-only torch on purpose -- af3_jax's lock does, for its
        # weights converter -- and a check that reads torch alone then reports a
        # working provider as broken. `_arch_problem` in remote_resident.setup
        # had this same defect and refused af3_jax outright; this one only made
        # `tu remote check` print a red line, which is the quieter and therefore
        # longer-lived version of the same mistake.
        try:
            import jax
            import jax.numpy as jnp
            gpu["jax_version"] = str(jax.__version__)
            gpu["jax_backend"] = str(jax.default_backend())
            devs = (
                jax.local_devices(backend="gpu")
                if gpu["jax_backend"] == "gpu"
                else []
            )
            if devs:
                gpu["device"] = str(devs[0].device_kind)
                gpu["capability"] = str(getattr(devs[0], "compute_capability", ""))
                # The same 28.0 the torch branch produces, and real device work
                # rather than a capability read: a CUDA context that reports
                # itself healthy can still fail on the first kernel.
                gpu["tensor_sum"] = float(jnp.arange(8).sum())
                gpu["cuda_available"] = True
        except Exception as exc:
            gpu["jax_error"] = f"{{type(exc).__name__}}: {{exc}}"
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


def provider_manifest(deployment: RemoteDeployment):
    """The provider's ``provider.toml``, or None when it declares none yet.

    Providers are being moved onto that manifest one at a time; one without it
    is checked exactly as before, so this returns None rather than raising.
    """
    try:
        from tooluniverse.remote_resident import manifest as _m
    except Exception:  # noqa: BLE001 - a missing TOML parser must not fail a check
        return None
    package = ".".join(deployment.module.split(".")[:-1])
    spec = importlib.util.find_spec(package)
    if spec is None or not spec.submodule_search_locations:
        return None
    path = Path(list(spec.submodule_search_locations)[0]) / _m.MANIFEST_NAME
    if not path.is_file():
        return None
    try:
        return _m.load(path)
    except Exception:  # noqa: BLE001 - reported by the caller as a named problem
        return None


_MODEL_ENV_PROBE = """
import json, shutil, sys
result = {"python_version": list(sys.version_info[:3]),
          "commands": {name: shutil.which(name) is not None for name in COMMANDS}}
gpu = {"torch_available": False, "cuda_available": False}
try:
    import torch
    gpu["torch_available"] = True
    gpu["torch_version"] = str(torch.__version__)
    gpu["cuda_available"] = bool(torch.cuda.is_available())
    if gpu["cuda_available"]:
        gpu["device"] = str(torch.cuda.get_device_name(0))
        gpu["capability"] = "%d.%d" % torch.cuda.get_device_capability(0)
        gpu["tensor_sum"] = float(torch.arange(8, device="cuda").sum().item())
except Exception as exc:
    gpu["error"] = "%s: %s" % (type(exc).__name__, exc)
if not gpu["cuda_available"]:
    # See the note in _provider_probe_code: a provider may drive the card with
    # JAX while its torch is CPU-only by design.
    try:
        import jax
        import jax.numpy as jnp
        gpu["jax_version"] = str(jax.__version__)
        gpu["jax_backend"] = str(jax.default_backend())
        devs = jax.local_devices(backend="gpu") if gpu["jax_backend"] == "gpu" else []
        if devs:
            gpu["device"] = str(devs[0].device_kind)
            gpu["capability"] = str(getattr(devs[0], "compute_capability", ""))
            gpu["tensor_sum"] = float(jnp.arange(8).sum())
            gpu["cuda_available"] = True
    except Exception as exc:
        gpu["jax_error"] = "%s: %s" % (type(exc).__name__, exc)
result["gpu"] = gpu
for name in LAUNCH_MODULES:
    try:
        __import__(name)
        result.setdefault("modules", {})[name] = True
    except Exception as exc:
        result.setdefault("modules", {})[name] = "%s: %s" % (type(exc).__name__, exc)
print(json.dumps(result, sort_keys=True))
"""


def check_model_environment(
    manifest, *, launch_modules: tuple[str, ...] = (), timeout: float = 60
) -> dict[str, Any]:
    """Probe the interpreter the model itself runs in.

    A resident provider splits in two: a light MCP server in ToolUniverse's
    environment and the model in its own, because their pinned stacks do not
    coexist. `boltz` on PATH and a working CUDA tensor are properties of the
    second, and checking them in the first reports a broken deployment that is
    in fact correctly separated.
    """
    out: dict[str, Any] = {"declared_python": manifest.env_python}
    try:
        python = manifest.python_executable()
    except Exception as exc:  # noqa: BLE001 - the reason is the answer
        return {**out, "ok": False, "error": str(exc)}
    out["python"] = python
    if not Path(python).is_file():
        return {**out, "ok": False, "error": f"{python}: not a file"}
    code = _MODEL_ENV_PROBE.replace(
        "COMMANDS", json.dumps(list(_model_commands(manifest)))
    ).replace("LAUNCH_MODULES", json.dumps(list(launch_modules)))
    # The model environment's console scripts sit beside its interpreter; a
    # probe inheriting only this process's PATH would not see them and would
    # report a correctly installed model as missing its command.
    env = dict(os.environ)
    # NOT resolve(): a venv's bin/python is a symlink to the interpreter it was
    # created from, and following it lands in that interpreter's bin directory
    # instead of the venv's -- where the console scripts actually are.
    bin_dir = str(Path(python).expanduser().absolute().parent)
    env["PATH"] = bin_dir + (os.pathsep + env["PATH"] if env.get("PATH") else "")
    try:
        completed = subprocess.run(
            [python, "-c", code],
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {**out, "ok": False, "error": f"{type(exc).__name__}"}
    lines = completed.stdout.strip().splitlines()
    try:
        probe = json.loads(lines[-1] if lines else "")
    except (json.JSONDecodeError, TypeError):
        return {
            **out,
            "ok": False,
            "error": "the model environment's probe returned invalid output",
            "exit_code": completed.returncode,
        }
    gpu = probe.get("gpu") or {}
    gpu_ok = manifest.gpu_policy != "required" or (
        gpu.get("cuda_available") is True and gpu.get("tensor_sum") == 28.0
    )
    modules_ok = all(v is True for v in (probe.get("modules") or {}).values())
    return {
        **out,
        "ok": bool(
            gpu_ok and modules_ok and all((probe.get("commands") or {}).values())
        ),
        **probe,
    }


def _model_commands(manifest) -> tuple[str, ...]:
    """Commands the model environment must carry, from its slug's deployment."""
    deployment = REMOTE_BY_SLUG.get(manifest.slug)
    return tuple(deployment.required_commands) if deployment else ()


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

    # A provider that declares `mode = "resident"` runs the model in its own
    # environment, so `boltz` on PATH and a working CUDA tensor are properties
    # of THAT interpreter, not of the one serving MCP. Checking them here would
    # fail a deployment that is separated exactly as the manifest asks.
    manifest = provider_manifest(deployment)
    model_env: dict[str, Any] | None = None
    weights: dict[str, Any] | None = None
    if manifest is not None:
        problems = manifest.verify_weights()
        weights = {
            "root": str(manifest.weights_root() or ""),
            "declared": [w.name for w in manifest.weights],
            "problems": problems,
            "ok": not problems,
        }
        if manifest.mode == "resident":
            launch_modules = ()
            if manifest.launch:
                # The kit (or whatever the launcher imports) has to be present
                # in the model environment, not in this one.
                launch_modules = ("boltz2_opt",) if manifest.slug == "boltz" else ()
            model_env = check_model_environment(
                manifest, launch_modules=launch_modules, timeout=timeout
            )
            commands_ok = True  # asked of the model environment instead
            gpu_ok = True if not gpu_required else bool(model_env.get("ok"))

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
        and (weights is None or weights["ok"])
        and (model_env is None or model_env.get("ok") is True)
    )
    return {
        "ok": ok,
        "implementation": deployment.slug,
        "manifest": (
            None
            if manifest is None
            else {
                "mode": manifest.mode,
                "vram_budget_gb": manifest.vram_budget_gb,
                "isolation": manifest.isolation,
                "path": str(manifest.path),
            }
        ),
        "weights": weights,
        "model_environment": model_env,
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
    extra_env: Iterable[str] = (),
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
            env=child_environment(python, deployment, extra_env=extra_env),
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
    extra_env: Iterable[str] = (),
) -> tuple[ManagedRemoteProcess | None, dict[str, Any]]:
    """Reuse an exact endpoint or start a provider and validate it."""

    current = discover_endpoint(deployment, timeout=2)
    if current.get("reachable"):
        if not current.get("ok"):
            raise RuntimeError(
                f"port {deployment.port} is serving a different MCP tool set"
            )
        return None, current

    managed = start_provider(
        deployment, python=python, log_dir=log_dir, extra_env=extra_env
    )
    try:
        ready = wait_until_ready(deployment, managed, timeout=startup_timeout)
    except Exception:
        stop_provider(managed)
        raise
    return managed, ready
