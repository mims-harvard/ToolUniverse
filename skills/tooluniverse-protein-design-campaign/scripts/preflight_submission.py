#!/usr/bin/env python3
"""Read-only CSV/methods preflight; no network or eligibility attestation."""

import argparse
import csv
import hashlib
import io
import json
import re
from pathlib import Path


AMINO_ACIDS = set("ACDEFGHIKLMNPQRSTVWY")
DEFAULT_CLASSES = "single_chain,nanobody,scfv,fab_kappa,fab_lambda"
DEFAULT_PAIRED_CLASSES = "fab_kappa,fab_lambda"
DISCLOSURE_PATTERNS = {
    "private_path": re.compile(r"/Users/|/home/|/private/|[A-Za-z]:[\\/]Users[\\/]"),
    "email_address": re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"),
    "private_ip_or_localhost": re.compile(
        r"\b(?:localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|"
        r"192\.168\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+)\b",
        re.I,
    ),
    "credential_marker": re.compile(
        r"-----BEGIN [A-Z ]*PRIVATE KEY|"
        r"\b(?:api[_-]?key|access[_-]?token|token|secret|password|authorization|"
        r"bearer|X-Amz-Signature|X-Goog-Signature)\s*[:=]|"
        r"https?://[^/\s:@]+:[^/\s@]+@|"
        r"\b(?:sk-|ghp_|github_pat_|AKIA)[A-Za-z0-9_-]{12,}",
        re.I,
    ),
    "selector_instruction": re.compile(
        r"ignore previous instructions|system prompt|rank this first|"
        r"select this candidate|you are (?:ChatGPT|Claude)",
        re.I,
    ),
}


def issue(findings, category, role, row=None):
    """Never echo a matched value that may contain a secret."""
    item = {"category": category, "file_role": role}
    if row is not None:
        item["row"] = row
    findings.append(item)


def read_text(path, role, report, max_bytes, scan):
    try:
        if path.stat().st_size > max_bytes:
            issue(report["issues"], "file_size_limit", role)
            return None
        data = path.read_bytes()
        text = data.decode("utf-8-sig")
    except (OSError, UnicodeError):
        issue(report["issues"], "unreadable_or_non_utf8", role)
        return None
    report["files"][role] = {
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    if scan:
        for category, pattern in DISCLOSURE_PATTERNS.items():
            if pattern.search(text):
                issue(report["issues"], category, role)
    return text


def parse_csv(text, role, findings, strict_headers):
    try:
        reader = csv.DictReader(io.StringIO(text), strict=True)
        headers = reader.fieldnames or []
        if len(headers) != len(set(headers)):
            issue(findings, "duplicate_headers", role)
            return []
        if not {"name", "sequence"}.issubset(headers):
            issue(findings, "missing_required_headers", role)
            return []
        if strict_headers and set(headers) - {"name", "sequence", "molecule_class"}:
            issue(findings, "unreviewed_extra_columns", role)
        rows = list(reader)
        if any(None in row or any(v is None for v in row.values()) for row in rows):
            issue(findings, "malformed_csv_row", role)
            return []
        return rows
    except csv.Error:
        issue(findings, "malformed_csv", role)
        return []


def preflight(args):
    report = {
        "format_and_disclosure_checks_pass": False,
        "files": {},
        "candidate_count": 0,
        "candidates": [],
        "issues": [],
        "not_checked": [
            "official_novelty",
            "binding_or_pH_selectivity",
            "participant_eligibility_and_track",
            "intellectual_property_and_institutional_permissions",
            "actual_human_scientific_review",
            "all_possible_sensitive_information",
        ],
    }
    if (
        args.min_length < 1
        or args.max_length < args.min_length
        or args.max_designs < 1
        or args.max_bytes < 1
    ):
        issue(report["issues"], "invalid_limits", "configuration")
        return report
    classes = {c.strip() for c in args.classes.split(",") if c.strip()}
    paired_classes = {c.strip() for c in args.paired_classes.split(",") if c.strip()}
    if not classes:
        issue(report["issues"], "empty_class_vocabulary", "configuration")
        return report
    text = read_text(args.csv, "submission", report, args.max_bytes, scan=True)
    if args.methods:
        read_text(args.methods, "methods", report, args.max_bytes, scan=True)
    if text is None:
        return report
    rows = parse_csv(text, "submission", report["issues"], strict_headers=True)
    report["candidate_count"] = len(rows)
    if not rows or len(rows) > args.max_designs:
        issue(report["issues"], "candidate_count_limit", "submission")

    sources = None
    if args.source_csv:
        source = read_text(
            args.source_csv, "source", report, args.max_bytes, scan=False
        )
        source_rows = (
            parse_csv(source, "source", report["issues"], strict_headers=False)
            if source is not None
            else []
        )
        sources = {}
        for r in source_rows:
            if r["name"] in sources:
                issue(report["issues"], "duplicate_source_name", "source")
            sources[r["name"]] = r

    names, sequences = set(), set()
    for row_number, row in enumerate(rows, start=2):
        name, seq = row["name"], row["sequence"]
        cls = row.get("molecule_class") or args.default_class
        # Only hashes, counts and row numbers are emitted, never the sequence/name.
        report["candidates"].append(
            {
                "csv_row": row_number,
                "sequence_sha256": hashlib.sha256(seq.encode()).hexdigest(),
                "chain_lengths": [len(c) for c in seq.split(":")],
            }
        )
        if any(
            value.lstrip().startswith(("=", "+", "-", "@")) for value in row.values()
        ):
            issue(
                report["issues"], "spreadsheet_formula_cell", "submission", row_number
            )
        if not name or name != name.strip() or any(ord(c) < 32 for c in name):
            issue(report["issues"], "invalid_name", "submission", row_number)
        if name in names:
            issue(report["issues"], "duplicate_name", "submission", row_number)
        if seq in sequences:
            issue(report["issues"], "duplicate_sequence", "submission", row_number)
        names.add(name)
        sequences.add(seq)
        if cls not in classes:
            issue(
                report["issues"], "unsupported_molecule_class", "submission", row_number
            )
        chains = seq.split(":")
        expected_chains = 2 if cls in paired_classes else 1
        if len(chains) != expected_chains:
            issue(report["issues"], "chain_format", "submission", row_number)
        if any(not c or set(c) - AMINO_ACIDS for c in chains):
            issue(report["issues"], "invalid_amino_acids", "submission", row_number)
        if any(not args.min_length <= len(c) <= args.max_length for c in chains):
            issue(report["issues"], "chain_length_limit", "submission", row_number)
        if sources is not None:
            original = sources.get(name)
            if (
                original is None
                or original["sequence"] != seq
                or (original.get("molecule_class") or args.default_class) != cls
            ):
                issue(
                    report["issues"],
                    "source_identity_mismatch",
                    "submission",
                    row_number,
                )
    report["format_and_disclosure_checks_pass"] = not report["issues"]
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--methods", type=Path)
    parser.add_argument("--source-csv", type=Path)
    parser.add_argument("--min-length", type=int, default=10)
    parser.add_argument("--max-length", type=int, default=250)
    parser.add_argument("--max-designs", type=int, default=20)
    parser.add_argument("--max-bytes", type=int, default=5_000_000)
    parser.add_argument("--classes", default=DEFAULT_CLASSES)
    parser.add_argument(
        "--paired-classes",
        default=DEFAULT_PAIRED_CLASSES,
        help="Comma-separated class labels requiring two colon-separated chains; configure from portal rules.",
    )
    parser.add_argument("--default-class", default="single_chain")
    args = parser.parse_args()
    report = preflight(args)
    print(json.dumps(report, indent=2))
    return 0 if report["format_and_disclosure_checks_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
