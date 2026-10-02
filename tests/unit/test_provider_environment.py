"""What a provider process is allowed to see of the machine it runs on.

A provider used to inherit a copy of the whole environment with two platform keys removed.
That is fine while a machine only serves its owner and wrong the moment it serves anyone
else: reviewed provider code would run holding every unrelated credential in the owner's
shell, and a caller's work could quietly spend the owner's paid API quota.

These tests pin the allowlist from both directions -- the credentials that must not get
through, and the infrastructure a provider genuinely needs so the restriction does not
simply break GPU and R deployments.

No subprocesses, no network.
"""

from __future__ import annotations

import pytest

from tooluniverse.remote_runtime import (
    PROVIDER_ENV_PREFIXES,
    REMOTE_BY_SLUG,
    RemoteDeployment,
    child_environment,
    provider_environment_names,
)

PLAIN = RemoteDeployment(slug="plain", module="x", port=9001, operations=("plain_op",))
WITH_DECLARED = RemoteDeployment(
    slug="declared",
    module="x",
    port=9002,
    operations=("declared_op",),
    required_env=("USPTO_API_KEY", "DEPMAP_DATA_PATH"),
    path_env=("DEPMAP_DATA_PATH",),
)


def env(monkeypatch, **values: str) -> None:
    for name, value in values.items():
        monkeypatch.setenv(name, value)


# ── what must not get through ───────────────────────────────────────────────────


@pytest.mark.parametrize(
    "name",
    [
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "GITHUB_TOKEN",
        "DATABASE_URL",
        "HF_TOKEN",
        "NCBI_API_KEY",
        "SLACK_BOT_TOKEN",
        "GOOGLE_APPLICATION_CREDENTIALS",
    ],
)
def test_an_unrelated_credential_does_not_reach_a_provider(monkeypatch, name):
    """The owner's other keys are not this provider's business.

    Each of these would previously have been inherited. A provider that logs its
    environment on a crash, or makes an outbound request that picks a key up from it,
    would carry the owner's credential somewhere they never agreed to.
    """
    env(monkeypatch, **{name: "secret-value"})

    assert name not in child_environment("/usr/bin/python3", PLAIN)


def test_the_platform_key_is_withheld_even_if_a_provider_declares_it(monkeypatch):
    """Nothing a provider computes has any business authenticating this machine."""
    sneaky = RemoteDeployment(
        slug="sneaky",
        module="x",
        port=9003,
        operations=("op",),
        required_env=("TOOLUNIVERSE_SERVICE_KEY", "TU_SERVICE_KEY"),
    )
    env(monkeypatch, TOOLUNIVERSE_SERVICE_KEY="tu-sk-aaa", TU_SERVICE_KEY="tu-sk-bbb")

    result = child_environment("/usr/bin/python3", sneaky)

    assert "TOOLUNIVERSE_SERVICE_KEY" not in result
    assert "TU_SERVICE_KEY" not in result


# HF_TOKEN lives in the same family as HF_HOME. A prefix allowlist for HF_ would hand over
# an access token in order to pass a cache directory, which is why that family is listed by
# exact name instead.
def test_the_prefix_families_cannot_smuggle_a_token(monkeypatch):
    assert not any(prefix.startswith("HF") for prefix in PROVIDER_ENV_PREFIXES)
    env(monkeypatch, HF_TOKEN="hf_secret", HF_HOME="/models")

    result = child_environment("/usr/bin/python3", PLAIN)

    assert "HF_TOKEN" not in result
    assert result.get("HF_HOME") == "/models"


def test_ld_preload_is_never_passed(monkeypatch):
    """No reviewed provider needs it, and it is how arbitrary code enters a process."""
    env(monkeypatch, LD_PRELOAD="/tmp/evil.so", LD_LIBRARY_PATH="/usr/local/cuda/lib64")

    result = child_environment("/usr/bin/python3", PLAIN)

    assert "LD_PRELOAD" not in result
    assert result.get("LD_LIBRARY_PATH") == "/usr/local/cuda/lib64"


# ── what must still get through ─────────────────────────────────────────────────


def test_a_provider_receives_exactly_what_it_declared(monkeypatch):
    env(
        monkeypatch,
        USPTO_API_KEY="uspto-key",
        DEPMAP_DATA_PATH="/data/depmap",
        OPENAI_API_KEY="unrelated",
    )

    result = child_environment("/usr/bin/python3", WITH_DECLARED)

    assert result["USPTO_API_KEY"] == "uspto-key"
    assert result["DEPMAP_DATA_PATH"] == "/data/depmap"
    assert "OPENAI_API_KEY" not in result


def test_gpu_selection_and_tuning_survive(monkeypatch):
    """Restricting the environment must not quietly turn a GPU provider into a CPU one."""
    env(
        monkeypatch,
        CUDA_VISIBLE_DEVICES="1",
        CUDA_HOME="/usr/local/cuda",
        NVIDIA_VISIBLE_DEVICES="all",
        NCCL_DEBUG="INFO",
        OMP_NUM_THREADS="8",
        MKL_NUM_THREADS="8",
    )

    result = child_environment("/usr/bin/python3", PLAIN)

    for name in (
        "CUDA_VISIBLE_DEVICES",
        "CUDA_HOME",
        "NVIDIA_VISIBLE_DEVICES",
        "NCCL_DEBUG",
        "OMP_NUM_THREADS",
        "MKL_NUM_THREADS",
    ):
        assert name in result, f"{name} was dropped"


def test_r_providers_keep_their_library_paths(monkeypatch):
    """monocle3, singler, slingshot and liana all shell out to Rscript."""
    env(monkeypatch, R_HOME="/usr/lib/R", R_LIBS_USER="/home/me/R/library")

    result = child_environment("/usr/bin/python3", PLAIN)

    assert result["R_HOME"] == "/usr/lib/R"
    assert result["R_LIBS_USER"] == "/home/me/R/library"


@pytest.mark.parametrize(
    "name, value",
    [
        ("HOME", "/home/me"),
        ("TMPDIR", "/scratch"),
        ("LANG", "en_US.UTF-8"),
        ("HTTPS_PROXY", "http://proxy:3128"),
        ("REQUESTS_CA_BUNDLE", "/etc/ssl/corp.pem"),
        ("XDG_CACHE_HOME", "/cache"),
        ("CONDA_PREFIX", "/opt/conda/envs/boltz"),
    ],
)
def test_infrastructure_a_process_cannot_work_without_survives(
    monkeypatch, name, value
):
    env(monkeypatch, **{name: value})

    assert child_environment("/usr/bin/python3", PLAIN).get(name) == value


def test_the_runtime_still_sets_what_the_provider_is_told_to_bind(monkeypatch):
    result = child_environment("/usr/bin/python3", PLAIN)

    assert result["TOOLUNIVERSE_MCP_HOST"] == "127.0.0.1"
    assert result["TOOLUNIVERSE_MCP_PORT"] == str(PLAIN.port)
    assert result["PYTHONUNBUFFERED"] == "1"
    assert result["PATH"].startswith("/usr/bin")


# ── the operator's escape hatch ─────────────────────────────────────────────────


def test_a_site_can_pass_one_more_variable_explicitly(monkeypatch):
    """Guessing every site's needs is impossible; the decision stays with the operator."""
    env(monkeypatch, SITE_LICENCE_SERVER="licence.internal:7070", OPENAI_API_KEY="no")

    result = child_environment(
        "/usr/bin/python3", PLAIN, extra_env=["SITE_LICENCE_SERVER"]
    )

    assert result["SITE_LICENCE_SERVER"] == "licence.internal:7070"
    assert "OPENAI_API_KEY" not in result, "the hatch must not widen anything else"


def test_an_empty_name_in_the_hatch_is_ignored(monkeypatch):
    names = provider_environment_names(PLAIN, extra=["", None])  # type: ignore[list-item]

    assert "" not in names and None not in names


# ── against the real catalog ─────────────────────────────────────────────────────


def test_every_reviewed_provider_can_still_see_what_it_declared(monkeypatch):
    """A restriction that breaks the shipped catalog is not a security improvement."""
    for deployment in REMOTE_BY_SLUG.values():
        for name in (*deployment.required_env, *deployment.path_env):
            monkeypatch.setenv(name, f"value-for-{name}")

    for deployment in REMOTE_BY_SLUG.values():
        result = child_environment("/usr/bin/python3", deployment)
        for name in (*deployment.required_env, *deployment.path_env):
            assert result.get(name) == f"value-for-{name}", (
                f"{deployment.slug} lost its declared {name}"
            )


def test_only_one_reviewed_provider_declares_a_credential():
    """Recorded because it is why this allowlist is cheap.

    Everything else the catalog declares is a data path, so withholding the rest of the
    environment costs the catalog nothing. A second credential appearing here is a prompt
    to check that it is really meant to be readable by that provider.
    """
    credentials = {
        name
        for deployment in REMOTE_BY_SLUG.values()
        for name in deployment.required_env
        if name.endswith(("_API_KEY", "_TOKEN", "_SECRET", "_PASSWORD"))
    }

    assert credentials == {"USPTO_API_KEY"}, credentials
