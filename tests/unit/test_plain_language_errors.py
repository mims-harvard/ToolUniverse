"""An environment check that fails has to say what to do about it.

The CLI read the reason out of report["checks"], a key check_environment has never produced,
so every provider on every machine was excluded with the words "environment check failed" and
nothing else. The reason was computed and then discarded.

That matters most for the people this is for. A biologist whose virtual environment is Python
3.11 cannot act on "environment check failed"; they can act on "needs Python 3.12, this one
is 3.11".
"""

from __future__ import annotations

import pathlib

import pytest

from tooluniverse.remote_runtime import (
    REMOTE_BY_SLUG,
    explain_environment_failure,
)

MOFA = REMOTE_BY_SLUG["mofa"]
BOLTZ = REMOTE_BY_SLUG["boltz"]


def only(report: dict, deployment=MOFA) -> str:
    lines = explain_environment_failure(report, deployment)
    assert lines, "a failure explained itself with nothing"
    return " ".join(lines)


# ── the reason is never missing ──────────────────────────────────────────────────


def test_a_failure_always_explains_itself():
    """Even a report with nothing recognisable in it must produce a next move."""
    message = only({"ok": False})

    assert "tu remote check mofa" in message


@pytest.mark.parametrize(
    "report",
    [
        {"ok": False},
        {"ok": False, "provider": {}},
        {"ok": False, "provider": {"module_available": True, "commands": {}}},
        {"ok": False, "python_supported_3_12": True, "provider": {}},
    ],
)
def test_no_report_shape_produces_an_empty_explanation(report):
    assert explain_environment_failure(report, MOFA) != []


# ── each cause, in words with a fix in them ──────────────────────────────────────


def test_the_wrong_python_says_which_version_and_how_to_make_one():
    message = only({
        "ok": False, "python_supported_3_12": False,
        "provider": {"python_version": [3, 11, 12]},
    })

    assert "3.12" in message and "3.11" in message
    assert "python3.12 -m venv" in message


def test_the_wrong_python_hides_the_consequences_of_itself():
    """Packages are 'missing' because they were installed under another interpreter.

    Listing them as separate problems sends someone to install things they already have.
    """
    lines = explain_environment_failure({
        "ok": False, "python_supported_3_12": False,
        "provider": {"python_version": [3, 11], "module_available": False,
                     "commands": {"Rscript": False}},
    }, MOFA)

    assert len(lines) == 1, lines


def test_a_missing_package_points_at_its_own_setup_guide():
    message = only({
        "ok": False, "python_supported_3_12": True,
        "provider": {"module_available": False, "commands": {}},
    })

    assert "not installed" in message
    assert "skills/setup-mofa-remote-tool" in message


def test_a_missing_command_names_the_command():
    message = only({
        "ok": False, "python_supported_3_12": True,
        "provider": {"module_available": True, "commands": {"boltz": False}},
    }, BOLTZ)

    assert "`boltz`" in message and "PATH" in message


def test_no_gpu_offers_the_cpu_flag_and_says_what_it_costs():
    message = only({
        "ok": False, "python_supported_3_12": True, "gpu_policy": "required",
        "cpu_override": False,
        "provider": {"module_available": True, "commands": {"boltz": True},
                     "gpu": {"cuda_available": False}},
    }, BOLTZ)

    assert "--allow-cpu" in message
    assert "slower" in message


def test_a_broken_cuda_install_is_not_reported_as_a_missing_gpu():
    """Different problem, different fix: the GPU is there and the stack is wrong."""
    message = only({
        "ok": False, "python_supported_3_12": True, "gpu_policy": "required",
        "cpu_override": False,
        "provider": {"module_available": True, "commands": {"boltz": True},
                     "gpu": {"cuda_available": True, "tensor_sum": 3.0}},
    }, BOLTZ)

    assert "not working" in message
    assert "--allow-cpu" not in message


def test_an_unset_variable_is_named():
    message = only({
        "ok": False, "python_supported_3_12": True,
        "provider": {"module_available": True, "commands": {}},
        "provider_environment": [{"name": "DEPMAP_DATA_PATH", "set": False}],
    })

    assert "DEPMAP_DATA_PATH" in message and "not set" in message


def test_a_variable_pointing_nowhere_is_distinguished_from_an_unset_one():
    message = only({
        "ok": False, "python_supported_3_12": True,
        "provider": {"module_available": True, "commands": {}},
        "provider_environment": [
            {"name": "DEPMAP_DATA_PATH", "set": True, "path_exists": False}],
    })

    assert "does not exist" in message
    assert "not set" not in message


def test_not_being_signed_in_names_the_command_that_signs_in():
    message = only({
        "ok": False, "python_supported_3_12": True,
        "provider": {"module_available": True, "commands": {}},
        "share_prerequisites": {"requested": True, "sdk_available": True,
                                "service_key_set": False},
    })

    assert "tu remote login" in message


def test_sharing_prerequisites_are_silent_when_sharing_was_not_asked_for():
    lines = explain_environment_failure({
        "ok": False, "python_supported_3_12": True,
        "provider": {"module_available": False, "commands": {}},
        "share_prerequisites": {"requested": False, "sdk_available": False,
                                "service_key_set": False},
    }, MOFA)

    assert not any("signed in" in line or "tuplatform-connect" in line for line in lines)


# ── what the words point at has to exist ─────────────────────────────────────────


def test_every_provider_has_the_setup_guide_this_names():
    """The message sends people to skills/setup-<slug>-remote-tool, so it must be there."""
    missing = [
        slug for slug in REMOTE_BY_SLUG
        if not (pathlib.Path(__file__).resolve().parents[2]
                / "skills" / f"setup-{slug}-remote-tool").is_dir()
    ]

    assert missing == [], missing


def test_a_provider_failure_never_leaks_what_the_probe_printed():
    """A provider's stderr can carry a credential, so only its exit code is reported."""
    message = only({
        "ok": False,
        "provider": {"error": "provider preflight returned invalid output",
                     "exit_code": 1, "stderr": "token=sk-SECRET"},
    })

    assert "SECRET" not in message
    assert "exit code 1" in message


# ── a suggested port is checked before it is offered ─────────────────────────────


def test_the_suggested_port_is_actually_free():
    """Offering a number without checking is how one collision becomes two.

    7999 + 1 is 8000, which no reviewed provider uses and which is also where a locally
    running platform listens, so someone following that advice meets the same error again.
    """
    import socket

    from tooluniverse.remote_pool import suggest_free_port

    port = suggest_free_port(7999, REMOTE_BY_SLUG.values())

    assert port is not None
    probe = socket.socket()
    try:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(("127.0.0.1", port))
    finally:
        probe.close()


def test_the_suggestion_skips_ports_that_are_in_use_right_now():
    import socket

    from tooluniverse.remote_pool import suggest_free_port

    held = []
    try:
        for candidate in (7999, 8000, 8001):
            sock = socket.socket()
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", candidate))
            except OSError:
                # Something else on this machine already listens there, which
                # is the condition under test; on a shared host 8000 often is.
                sock.close()
                continue
            sock.listen(1)
            held.append(sock)

        port = suggest_free_port(7999, REMOTE_BY_SLUG.values())

        assert port not in (7999, 8000, 8001), port
    finally:
        for sock in held:
            sock.close()


def test_the_suggestion_is_never_a_reviewed_providers_own_port():
    """8080 is boltz's. Sending the pool there would stop boltz from starting."""
    from tooluniverse.remote_pool import suggest_free_port

    taken = {deployment.port for deployment in REMOTE_BY_SLUG.values()}

    for start in (7999, 8007, 8079):
        port = suggest_free_port(start, REMOTE_BY_SLUG.values())
        assert port not in taken, (start, port)
        assert port != start


def test_no_free_port_nearby_is_reported_rather_than_guessed():
    from tooluniverse.remote_pool import suggest_free_port

    # Every candidate in range is declared taken, so there is nothing honest to suggest.
    class Everything:
        port = 0

    fake = [type("D", (), {"port": p})() for p in range(60000, 60045)]

    assert suggest_free_port(60000, fake) is None
