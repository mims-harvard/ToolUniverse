"""Local, bounded protein alignment input diagnostics without homology claims."""

import hashlib
import re
from pathlib import Path

from .base_tool import BaseTool
from .tool_registry import register_tool

MAX_BYTES = 8 * 1024 * 1024
MAX_ROWS = 20000
MAX_COLUMNS = 10000
AMINO_ACIDS = set("ACDEFGHIKLMNPQRSTVWYBXZJUO")


def read_alignment(arguments):
    sources = [
        k
        for k in ("alignment_path", "alignment_content")
        if arguments.get(k) is not None
    ]
    if len(sources) != 1:
        raise ValueError("Provide exactly one of alignment_path or alignment_content")
    kind = sources[0]
    value = arguments[kind]
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{kind} must be a nonempty string")
    if kind == "alignment_path":
        with Path(value).expanduser().open("rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
    else:
        raw = value.encode("utf-8")
    if len(raw) > MAX_BYTES:
        raise ValueError("Alignment exceeds the 8 MiB input limit")
    return raw.decode("utf-8"), kind, hashlib.sha256(raw).hexdigest()


def parse_alignment(content, format_name):
    rows, parts, header = [], [], None

    def finish():
        if header is None:
            return
        sequence = "".join(parts)
        if not sequence:
            raise ValueError("Empty FASTA alignment record")
        if len(rows) >= MAX_ROWS:
            raise ValueError("Alignment exceeds the 20000-row input limit")
        if format_name == "a3m":
            insertion_count = sum(c.islower() for c in sequence)
            aligned = "".join(c for c in sequence if not c.islower() and c != ".")
            insertion_gap_count = sequence.count(".")
        else:
            insertion_count = insertion_gap_count = 0
            aligned = sequence.upper().replace(".", "-")
        if not aligned or len(aligned) > MAX_COLUMNS:
            raise ValueError("Aligned columns must be in 1..10000")
        if rows and len(aligned) != len(rows[0][0]):
            raise ValueError(
                "Unequal aligned lengths after format-specific insertion removal"
            )
        rows.append((aligned, insertion_count, insertion_gap_count))

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#"):
            # ColabFold complex A3M metadata requires splitting by component.
            if re.match(r"^#\d", line):
                raise ValueError(
                    "ColabFold complex/length metadata is unsupported; provide one component alignment"
                )
            continue
        if line.startswith(">"):
            finish()
            header, parts = line[1:].strip(), []
            if not header:
                raise ValueError("Empty FASTA header")
        else:
            if header is None:
                raise ValueError("Expected a FASTA header before sequence data")
            sequence = "".join(line.split())
            if set(sequence.upper()) - AMINO_ACIDS - {"-", "."}:
                raise ValueError("Invalid protein alignment characters")
            parts.append(sequence)
    finish()
    if not rows:
        raise ValueError("No FASTA alignment records")
    if not rows[0][0].replace("-", ""):
        raise ValueError("The first/query row contains no residues")
    return rows


@register_tool("ProteinMSAInventoryTool")
class ProteinMSAInventoryTool(BaseTool):
    def run(self, arguments):
        try:
            format_name = arguments.get("format")
            format_name = "a3m" if format_name is None else format_name
            if format_name not in ("a3m", "aligned_fasta"):
                raise ValueError("format must be a3m or aligned_fasta")
            limit = arguments.get("max_row_details")
            limit = 10 if limit is None else limit
            if type(limit) is not int or not 0 <= limit <= 100:
                raise ValueError("max_row_details must be an integer in 0..100")
            content, source, digest = read_alignment(arguments)
            rows = parse_alignment(content, format_name)
            query = rows[0][0]
            query_sequence = query.replace("-", "")
            expected = arguments.get("expected_query_sequence")
            if expected is not None:
                if not isinstance(expected, str) or not expected.strip():
                    raise ValueError(
                        "expected_query_sequence must be a nonempty protein sequence"
                    )
                expected = expected.strip().upper()
                if set(expected) - AMINO_ACIDS:
                    raise ValueError(
                        "expected_query_sequence must be an ungapped protein sequence"
                    )
            sites = [i for i, c in enumerate(query) if c != "-"]
            details, coverages, identities = [], [], []
            distinct = set()
            nongap_nonquery = 0
            insertion_residues = insertion_gaps = all_gap_rows = 0
            for index, (aligned, insertions, insert_gaps) in enumerate(rows):
                nongap = len(aligned.replace("-", ""))
                coverage = sum(aligned[i] != "-" for i in sites) / len(sites)
                identity = sum(aligned[i] == query[i] for i in sites) / len(sites)
                coverages.append(coverage)
                identities.append(identity)
                distinct.add(aligned)
                nongap_nonquery += bool(nongap and aligned != query)
                all_gap_rows += not bool(nongap)
                insertion_residues += insertions
                insertion_gaps += insert_gaps
                if index < limit:
                    details.append(
                        {
                            "row_index": index + 1,
                            "aligned_residue_count": nongap,
                            "query_site_coverage": coverage,
                            "query_site_identity": identity,
                            "insertion_residue_count": insertions,
                            "insertion_gap_count": insert_gaps,
                        }
                    )
            unique_nonquery = len(
                {s for s in distinct if s != query and s.replace("-", "")}
            )
            warnings = []
            if len(rows) == 1:
                warnings.append(
                    "Query-only alignment: no additional aligned sequence rows."
                )
            if len(rows) > len(distinct):
                warnings.append(
                    "Duplicate aligned rows inflate raw depth; unique count is reported separately."
                )
            if not unique_nonquery:
                warnings.append(
                    "No distinct nonempty nonquery aligned sequence; raw depth does not establish homolog support."
                )
            if all_gap_rows:
                warnings.append(
                    "All-gap rows contribute to raw depth but not nonempty sequence support."
                )
            if expected is not None and expected != query_sequence:
                warnings.append(
                    "The first/query sequence differs from expected_query_sequence."
                )
            data = {
                "source_kind": source,
                "input_sha256": digest,
                "format": format_name,
                "row_count": len(rows),
                "aligned_column_count": len(query),
                "query_residue_count": len(sites),
                "query_gap_count": query.count("-"),
                "unique_aligned_row_count": len(distinct),
                "duplicate_aligned_row_count": len(rows) - len(distinct),
                "nonempty_nonquery_row_count": nongap_nonquery,
                "unique_nonempty_nonquery_row_count": unique_nonquery,
                "all_gap_row_count": all_gap_rows,
                "query_only": len(rows) == 1,
                "has_distinct_nonquery_sequence": bool(unique_nonquery),
                "expected_query_matches": (
                    None if expected is None else expected == query_sequence
                ),
                "mean_query_site_coverage": sum(coverages) / len(rows),
                "mean_query_site_identity": sum(identities) / len(rows),
                "insertion_residue_count": insertion_residues,
                "insertion_gap_count": insertion_gaps,
                "row_details": details,
                "row_details_truncated": len(rows) > limit,
                "warnings": warnings,
                "homology_verified": False,
                "folding_verified": False,
                "limitations": [
                    "First record is treated as query; identity includes gaps as nonmatches at query residue columns.",
                    "Raw/unique row counts are not effective evolutionary depth (Neff). No homology search, paired-chain provenance, folding or binding validation.",
                    "A3M lower-case residues and dots are insertions; aligned_fasta lower-case residues are normalized and dots are gaps.",
                    "Inputs stay local. Output contains counts and hashes, not sequences or headers.",
                ],
            }
            return {"status": "success", "data": data}
        except (OSError, UnicodeError, ValueError, TypeError) as exc:
            return {"status": "error", "error": str(exc)}
