"""Lightweight entry point for the human-facing ``tu`` command."""

import os


def main() -> None:
    # Set this before importing the package. Console-script imports normally
    # initialize ``tooluniverse.__init__`` before ``tooluniverse.cli`` gets a
    # chance to opt into the provider-friendly lightweight path.
    previous = os.environ.get("TOOLUNIVERSE_LIGHT_IMPORT")
    os.environ.setdefault("TOOLUNIVERSE_LIGHT_IMPORT", "1")
    try:
        from tooluniverse.cli import main as cli_main
    finally:
        # This is an import-time optimization for the current CLI process, not
        # a user configuration.  Do not leak it into tools or child processes.
        if previous is None:
            os.environ.pop("TOOLUNIVERSE_LIGHT_IMPORT", None)
        else:
            os.environ["TOOLUNIVERSE_LIGHT_IMPORT"] = previous

    cli_main()
