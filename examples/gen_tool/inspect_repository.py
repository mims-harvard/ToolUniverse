"""Inspect Gen branch metadata using the normal ToolUniverse entry point."""

import argparse
import json
import os
import tempfile
from pathlib import Path

from tooluniverse import ToolUniverse


def _inspect(repository_path: str, view: str, branch: str | None, limit: int) -> None:
    universe = ToolUniverse()
    universe.load_tools(categories=["gen"])
    result = universe.run(
        {
            "name": "Gen_inspect_repository",
            "arguments": {
                "repository_path": repository_path,
                "view": view,
                "branch": branch,
                "limit": limit,
            },
        }
    )
    print(json.dumps(result, indent=2))


def _inspect_synthetic_repository(view: str, branch: str | None, limit: int) -> None:
    import gen

    previous_root = os.environ.get("TOOLUNIVERSE_GEN_ROOT")
    try:
        with tempfile.TemporaryDirectory(prefix="tooluniverse-gen-demo-") as root:
            os.environ["TOOLUNIVERSE_GEN_ROOT"] = root
            repository_path = Path(root) / "synthetic-genome"
            repository = gen.Repository(str(repository_path))
            repository.import_sequence(
                "ACGT", name="synthetic-contig", sample="synthetic-sample"
            )
            del repository
            _inspect(repository_path.name, view, branch, limit)
    finally:
        if previous_root is None:
            os.environ.pop("TOOLUNIVERSE_GEN_ROOT", None)
        else:
            os.environ["TOOLUNIVERSE_GEN_ROOT"] = previous_root


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "repository_path",
        nargs="?",
        help="Repository name inside TOOLUNIVERSE_GEN_ROOT",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Create and inspect a temporary synthetic four-base Gen repository",
    )
    parser.add_argument(
        "--view",
        choices=("branches", "operations", "samples"),
        default="branches",
    )
    parser.add_argument("--branch", help="Branch name for the operations view")
    parser.add_argument("--limit", type=int, default=20)
    arguments = parser.parse_args()

    if arguments.demo:
        if arguments.repository_path:
            parser.error("repository_path cannot be combined with --demo")
        _inspect_synthetic_repository(arguments.view, arguments.branch, arguments.limit)
    elif arguments.repository_path:
        _inspect(
            arguments.repository_path, arguments.view, arguments.branch, arguments.limit
        )
    else:
        parser.error("repository_path is required unless --demo is used")


if __name__ == "__main__":
    main()
