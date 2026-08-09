"""Lightweight entry point for the human-facing ``tu`` command."""

import os


def main() -> None:
    # Set this before importing the package. Console-script imports normally
    # initialize ``tooluniverse.__init__`` before ``tooluniverse.cli`` gets a
    # chance to opt into the provider-friendly lightweight path.
    os.environ.setdefault("TOOLUNIVERSE_LIGHT_IMPORT", "1")
    from tooluniverse.cli import main as cli_main

    cli_main()
