"""Administrator CLI for local, inert multi-format contract inspection."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .vsd_contracts import VSDContractError, inspect_contract_document


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tooluniverse-vsd-contracts")
    parser.add_argument("contract", type=Path, help="Local contract file")
    parser.add_argument(
        "--format",
        choices=[
            "openapi",
            "graphql",
            "asyncapi",
            "postman",
            "wsdl",
            "protobuf",
            "mcp",
        ],
        dest="format_hint",
        help="Override automatic format detection",
    )
    parser.add_argument(
        "--endpoint",
        help="Reviewed HTTPS endpoint when the format does not embed one",
    )
    parser.add_argument("--output", type=Path, help="Write the report to this file")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    namespace = build_parser().parse_args(argv)
    try:
        report = inspect_contract_document(
            namespace.contract,
            format_hint=namespace.format_hint,
            endpoint=namespace.endpoint,
        )
        rendered = (
            json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
        )
        if namespace.output:
            namespace.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
        return 0
    except (OSError, VSDContractError, ValueError) as exc:
        sys.stderr.write(json.dumps({"status": "error", "error": str(exc)}) + "\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
