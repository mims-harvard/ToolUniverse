"""Two machines shared the plain way must be two machines.

remote_server carries UNIQUE(user_id, name) and registration upserts on that pair, so a fixed
default name made the second machine a rename of the first. Driving the real stack showed it:
registering twice with the same name returned the same row id, and the account held one
machine instead of two. Someone who shares a laptop and then a lab box, both with the plain
command, silently loses one.
"""

from __future__ import annotations

import socket

from tooluniverse.cli import default_server_name


def test_the_name_is_this_machine_not_a_constant():
    host = socket.gethostname().split(".", 1)[0]

    assert default_server_name() == host


def test_a_suffix_separates_two_ways_of_sharing_the_same_machine():
    """One machine may forward an MCP server and share models at the same time."""
    assert default_server_name() != default_server_name("-models")
    assert default_server_name("-models").endswith("-models")


def test_a_domain_is_dropped_so_the_name_stays_readable(monkeypatch):
    monkeypatch.setattr(socket, "gethostname", lambda: "gpu-07.cluster.example.edu")

    assert default_server_name() == "gpu-07"


def test_an_unavailable_hostname_still_produces_a_name(monkeypatch):
    def unavailable() -> str:
        raise OSError("no hostname")

    monkeypatch.setattr(socket, "gethostname", unavailable)

    # Registration requires a non-empty name, so returning "" would turn a cosmetic problem
    # into a failure to share at all.
    assert default_server_name() == "this-computer"


def test_an_empty_hostname_still_produces_a_name(monkeypatch):
    monkeypatch.setattr(socket, "gethostname", lambda: "   ")

    assert default_server_name() == "this-computer"


def test_the_name_is_never_empty_and_carries_no_whitespace(monkeypatch):
    for value in ("", "   ", "box.example.com", "box"):
        monkeypatch.setattr(socket, "gethostname", lambda v=value: v)

        name = default_server_name()

        assert name.strip() == name and name != ""
