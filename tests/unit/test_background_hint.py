"""The command that turns a foreground share into one that survives the terminal.

Two things a person runs into and should not have to:

Closing the terminal takes the machine offline. And because this runs inside a virtual
environment, a new terminal answers "tu: command not found" -- the interpreter is only on PATH
while the environment is active. Measured: `env -i PATH=/usr/bin:/bin tu serve ...` produces
exactly that, from the shell, before any of this code runs, so it cannot be caught from inside.

A service unit records an absolute interpreter path and starts at boot, which removes both. So
the command that installs one is printed where the person is already looking, built from the
options they actually passed.
"""

from __future__ import annotations

import argparse
import shlex

import pytest

from tooluniverse.cli import background_command_for_pool

DEFAULTS = {
    "allow": "boltz,esm",
    "max_active": 1,
    "idle_ttl": 900.0,
    "vram_headroom": 1024,
    "allow_cpu": False,
    "pass_env": [],
    "python": "",
}


def built(name: str = "gpu-box", **overrides) -> str:
    return background_command_for_pool(
        argparse.Namespace(**{**DEFAULTS, **overrides}), name
    )


def test_the_plain_case_stays_short():
    """A line carrying every flag at its default is harder to read and no more faithful."""
    command = built()

    assert command == "tuplatform-service install --allow boltz,esm --name gpu-box"


def test_what_the_person_tuned_is_carried_over():
    command = built(max_active=2, idle_ttl=600.0, vram_headroom=2048, allow_cpu=True)

    for expected in ("--max-active 2", "--idle-ttl 600", "--vram-headroom 2048", "--allow-cpu"):
        assert expected in command, command


def test_a_default_is_not_repeated_as_though_it_were_a_choice():
    command = built(max_active=1, idle_ttl=900.0, vram_headroom=1024)

    for absent in ("--max-active", "--idle-ttl", "--vram-headroom", "--allow-cpu", "--python"):
        assert absent not in command, command


def test_each_passed_variable_appears_once():
    command = built(pass_env=["SITE_LICENCE", "OTHER"])

    assert command.count("--pass-env") == 2
    assert "--pass-env SITE_LICENCE" in command and "--pass-env OTHER" in command


def test_a_name_with_spaces_survives_being_pasted():
    command = built("gpu box 1")

    # shlex is what a shell does, so this is the question that matters.
    assert "--name" in shlex.split(command)
    assert shlex.split(command)[shlex.split(command).index("--name") + 1] == "gpu box 1"


def test_a_plain_name_is_not_quoted_for_no_reason():
    assert '"' not in built("gpu-box")


# ── the cross-repository contract ────────────────────────────────────────────────


def test_the_command_is_accepted_by_the_real_service_installer():
    """This builds flags that tuplatform-connect parses, and the two live in different repos.

    Each side can be correct alone while the pair does not fit: a renamed flag, a value
    argparse rejects, a name that loses its quoting. Neither repository's own suite would
    notice, because the mismatch is in the gap between them.
    """
    service = pytest.importorskip("tuplatform_connect.service")
    parser = service.build_parser()

    for overrides in (
        {},
        {"max_active": 2, "idle_ttl": 600.0, "vram_headroom": 2048, "allow_cpu": True,
         "pass_env": ["SITE_LICENCE", "OTHER"], "python": "/opt/p/bin/python"},
    ):
        argv = shlex.split(built("gpu box 1", **overrides))
        assert argv[:2] == ["tuplatform-service", "install"]

        args = parser.parse_args(argv[1:])

        wanted = {**DEFAULTS, **overrides}
        assert args.allow == wanted["allow"]
        assert args.name == "gpu box 1"
        assert args.max_active == wanted["max_active"]
        assert abs(args.idle_ttl - wanted["idle_ttl"]) < 1e-9
        assert args.vram_headroom == wanted["vram_headroom"]
        assert bool(args.allow_cpu) == wanted["allow_cpu"]
        assert (args.pass_env or []) == wanted["pass_env"]
        assert (args.python or "") == wanted["python"]
