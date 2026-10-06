"""Bounded coordinate inventory; never infer contents from a filename."""

import hashlib
import math
import re
from collections import Counter
from pathlib import Path

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

AA = dict(
    zip(
        "ALA ARG ASN ASP CYS GLN GLU GLY HIS ILE LEU LYS MET PHE PRO SER THR TRP TYR VAL".split(),
        "ARNDCQEGHILKMFPSTWYV",
    )
)
GLYCAN_NAMES = {"NAG", "MAN", "BMA", "FUC", "GAL", "GLC", "BGC", "SIA", "NGA", "NDG"}
MAX_BYTES = 4 * 1024 * 1024


def read_input(arguments):
    sources = [
        key
        for key in ("pdb_path", "pdb_content", "pdb_id")
        if arguments.get(key) is not None
    ]
    if len(sources) != 1:
        raise ValueError("Provide exactly one of pdb_path, pdb_content or pdb_id")
    kind = sources[0]
    value = arguments[kind]
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{kind} must be a nonempty string")
    if kind == "pdb_path":
        with Path(value).expanduser().open("rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
    elif kind == "pdb_content":
        raw = value.encode("utf-8")
    else:
        if not re.fullmatch(r"[1-9][A-Za-z0-9]{3}", value):
            raise ValueError("pdb_id must be a four-character legacy RCSB identifier")
        chunks, size = [], 0
        with requests.get(
            f"https://files.rcsb.org/download/{value.upper()}.pdb",
            stream=True,
            timeout=30,
        ) as response:
            response.raise_for_status()
            for chunk in response.iter_content(65536):
                size += len(chunk)
                if size > MAX_BYTES:
                    raise ValueError("PDB exceeds the 4 MiB input limit")
                chunks.append(chunk)
        raw = b"".join(chunks)
    if len(raw) > MAX_BYTES:
        raise ValueError("PDB exceeds the 4 MiB input limit")
    return raw.decode("utf-8"), kind, hashlib.sha256(raw).hexdigest()


def model_records(content):
    """Select models by file order, without pooling coordinates across models."""
    explicit = any(line[:6] == "MODEL " for line in content.splitlines())
    models, current = [], None
    if not explicit:
        if any(line[:6] == "ENDMDL" for line in content.splitlines()):
            raise ValueError("ENDMDL without MODEL")
        return [(None, content.splitlines())]
    for line in content.splitlines():
        record = line[:6]
        if record == "MODEL ":
            if current is not None:
                raise ValueError("Nested MODEL records")
            serial = int(line[10:14])
            current = []
            models.append((serial, current))
        elif record == "ENDMDL":
            if current is None:
                raise ValueError("ENDMDL without MODEL")
            current = None
        elif record in ("ATOM  ", "HETATM", "TER   "):
            if current is None:
                raise ValueError("Coordinate records outside MODEL/ENDMDL")
            current.append(line)
    if current is not None:
        raise ValueError("MODEL has no ENDMDL")
    return models


def element(line):
    symbol = line[76:78].strip().upper()
    if symbol:
        return symbol, False
    field = line[12:16]
    letters = re.sub("[^A-Za-z]", "", field).upper()
    if not letters:
        return "", True
    # Right-aligned protein CA is carbon; left-aligned CA is calcium.
    return (
        letters[:2] if field[0].isalpha() and len(letters) >= 2 else letters[:1]
    ), True


def inspect(lines, aliases, glycan_names, expected, detail_limit):
    residues, chains, coordinate_groups = {}, {}, {}
    atom_count = heavy_count = inferred_elements = unknown_elements = (
        alternate_count
    ) = 0
    kinds, glycan_kinds, ter_counts = Counter(), Counter(), Counter()
    glycan_atoms = glycan_heavy = 0
    noncontiguous, previous = set(), None
    for line in lines:
        record = line[:6]
        if record == "TER   ":
            ter_counts[line[21:22] or " "] += 1
            previous = None
            continue
        if record not in ("ATOM  ", "HETATM"):
            continue
        if len(line) < 54:
            raise ValueError("Truncated PDB coordinate record")
        coordinates = [float(line[i : i + 8]) for i in (30, 38, 46)]
        if not all(math.isfinite(x) for x in coordinates):
            raise ValueError("Nonfinite PDB atom coordinates")
        name, chain, number, insertion = (
            line[17:20].strip().upper(),
            line[21],
            int(line[22:26]),
            line[26:27].strip(),
        )
        key = (chain, number, insertion)
        if key != previous and key in residues:
            noncontiguous.add(key)
        previous = key
        row = residues.setdefault(
            key, {"names": set(), "atom_names": set(), "records": 0, "heavy_records": 0}
        )
        row["names"].add(name)
        row["atom_names"].add(line[12:16].strip())
        symbol, inferred = element(line)
        heavy = bool(symbol and symbol not in ("H", "D", "T"))
        if heavy:
            group = coordinate_groups.setdefault(
                tuple(coordinates), {"records": 0, "examples": []}
            )
            group["records"] += 1
            if len(group["examples"]) < 8:
                group["examples"].append(
                    {
                        "chain": chain,
                        "residue_number": number,
                        "insertion_code": insertion,
                        "residue_name": name,
                        "atom_name": line[12:16].strip(),
                        "alternate_location": line[16].strip(),
                    }
                )
        atom_count += 1
        heavy_count += heavy
        inferred_elements += inferred
        unknown_elements += not bool(symbol)
        alternate_count += bool(line[16].strip())
        kinds[record.strip()] += 1
        row["records"] += 1
        row["heavy_records"] += heavy
        chains.setdefault(
            chain,
            {
                "coordinate_records": 0,
                "heavy_coordinate_records": 0,
                "protein_rows": [],
                "residue_count": 0,
            },
        )
        chains[chain]["coordinate_records"] += 1
        chains[chain]["heavy_coordinate_records"] += heavy
        if name in glycan_names:
            glycan_atoms += 1
            glycan_heavy += heavy
            glycan_kinds[record.strip()] += 1
    if not atom_count:
        raise ValueError(
            "Expected PDB ATOM/HETATM records; FASTA and mmCIF are unsupported"
        )
    glycans, nonprotein, ambiguous = [], [], []
    for (chain, number, insertion), row in residues.items():
        names = sorted(row["names"])
        chains[chain]["residue_count"] += 1
        info = {
            "chain": chain,
            "residue_number": number,
            "insertion_code": insertion,
            "residue_names": names,
            "coordinate_records": row["records"],
            "heavy_coordinate_records": row["heavy_records"],
        }
        if len(names) > 1:
            ambiguous.append(info)
        canonical = aliases.get(names[0], names[0]) if len(names) == 1 else None
        if canonical in AA:
            chains[chain]["protein_rows"].append(
                {
                    **info,
                    "canonical_residue_name": canonical,
                    "one_letter": AA[canonical],
                    "classification": "standard" if names[0] in AA else "caller_alias",
                }
            )
        elif not any(n in glycan_names for n in names) and {"N", "CA", "C"}.issubset(
            row["atom_names"]
        ):
            chains[chain]["protein_rows"].append(
                {
                    **info,
                    "canonical_residue_name": None,
                    "one_letter": "X",
                    "classification": "backbone_name_heuristic",
                }
            )
        else:
            nonprotein.append(info)
        if any(n in glycan_names for n in names):
            glycans.append(info)
    for chain, row in chains.items():
        row["protein_residue_count"] = len(row["protein_rows"])
        row["coordinate_sequence"] = "".join(
            r["one_letter"] for r in row["protein_rows"]
        )
        row["TER_records"] = ter_counts[chain]
    observed = {
        c: r["protein_residue_count"]
        for c, r in chains.items()
        if r["protein_residue_count"]
    }
    detail_budget = detail_limit
    protein_details_truncated = False
    for row in chains.values():
        protein_details_truncated |= len(row["protein_rows"]) > detail_budget
        row["protein_rows"] = row["protein_rows"][:detail_budget]
        detail_budget -= len(row["protein_rows"])
    match = observed == expected if expected is not None else None
    warnings = []
    if alternate_count:
        warnings.append(
            "Alternate locations are counted as coordinate records; occupancies/altlocs were not resolved."
        )
    if inferred_elements:
        warnings.append("Some elements were inferred from PDB atom-name alignment.")
    if unknown_elements:
        warnings.append("Unknown elements are excluded from heavy-coordinate counts.")
    if ambiguous or noncontiguous:
        warnings.append(
            "Ambiguous or noncontiguous residue identifiers require review; coordinate sequences may be unreliable."
        )
    if match is False:
        warnings.append(
            "Observed protein chain lengths do not match the expected mapping; check missing, renamed or merged chains."
        )
    if not glycan_atoms:
        warnings.append(
            "No coordinates match the recognized glycan names; this does not prove absence of all glycans or occupancy."
        )
    coincident = [
        {"coordinates_A": list(xyz), **group}
        for xyz, group in coordinate_groups.items()
        if group["records"] > 1
    ]
    if coincident:
        warnings.append(
            "Exactly coincident heavy-coordinate records require review (possible placeholders or alternate locations); no clash calculation was performed."
        )
    return {
        "coordinate_records": atom_count,
        "heavy_coordinate_records": heavy_count,
        "record_types": dict(kinds),
        "alternate_location_records": alternate_count,
        "element_inferred_records": inferred_elements,
        "unknown_element_records": unknown_elements,
        "chains": chains,
        "observed_protein_chain_lengths": observed,
        "expected_chain_lengths_match": match,
        "recognized_glycan_residue_names": sorted(glycan_names),
        "recognized_glycan_residues": glycans[:detail_limit],
        "recognized_glycan_residue_count": len(glycans),
        "recognized_glycan_coordinate_records": glycan_atoms,
        "recognized_glycan_heavy_coordinate_records": glycan_heavy,
        "recognized_glycan_record_types": dict(glycan_kinds),
        "nonprotein_residues": nonprotein[:detail_limit],
        "nonprotein_residue_count": len(nonprotein),
        "ambiguous_residue_identifiers": ambiguous[:detail_limit],
        "ambiguous_residue_identifier_count": len(ambiguous),
        "residue_details_truncated": protein_details_truncated
        or any(len(x) > detail_limit for x in [glycans, nonprotein, ambiguous]),
        "max_residue_details": detail_limit,
        "noncontiguous_residue_identifier_count": len(noncontiguous),
        "coincident_heavy_coordinate_group_count": len(coincident),
        "coincident_heavy_coordinate_extra_records": sum(
            g["records"] - 1 for g in coincident
        ),
        "coincident_heavy_coordinate_groups": coincident[:50],
        "warnings": warnings,
        "structure_chemistry_verified": False,
        "binding_verified": False,
        "pH_selectivity_verified": False,
        "limitations": [
            "Coordinate inventory only; no chemical connectivity, glycan completeness, collision or binding validation.",
            "Coordinate sequence is not SEQRES or the biological full sequence; missing residues are not reconstructed.",
            "Glycan labels are a name-based subset plus caller labels, not a Chemical Component Dictionary classification.",
        ],
    }


def inspect_seqres(content, data, aliases, expected):
    """Compare declared polymer metadata with one selected coordinate model."""
    records, errors = {}, []
    for line_number, line in enumerate(content.splitlines(), 1):
        if line[:6] != "SEQRES":
            continue
        try:
            serial, chain, length = int(line[7:10]), line[11], int(line[13:17])
            names = line[19:70].split()
            if not 1 <= serial <= 999 or not 1 <= length <= 99999 or not names:
                raise ValueError
            if any(not re.fullmatch(r"[A-Za-z0-9]{1,3}", name) for name in names):
                raise ValueError
            records.setdefault(chain, []).append((serial, length, names))
        except (ValueError, IndexError):
            errors.append(f"Malformed SEQRES record at line {line_number}.")
    summaries, declared_protein_lengths = {}, {}
    for chain, rows in records.items():
        lengths = {row[1] for row in rows}
        serials = [row[0] for row in rows]
        names = [name.upper() for row in rows for name in row[2]]
        length = next(iter(lengths)) if len(lengths) == 1 else None
        consistent = length == len(names) and serials == list(range(1, len(rows) + 1))
        canonical = [aliases.get(name, name) for name in names]
        protein_names = all(name in AA for name in canonical)
        declared = "".join(AA[name] for name in canonical) if protein_names else None
        coordinate = data["chains"].get(chain, {}).get("coordinate_sequence", "")
        observed = len(coordinate)
        subsequence = None
        if (
            consistent
            and declared is not None
            and "X" not in coordinate
            and not data["noncontiguous_residue_identifier_count"]
        ):
            # Subsequence membership does not infer unique missing positions.
            iterator = iter(declared)
            subsequence = all(
                any(x == residue for x in iterator) for residue in coordinate
            )
        if not consistent:
            errors.append(
                f"Inconsistent SEQRES declarations, counts or serials for chain {chain!r}."
            )
        if subsequence is False:
            errors.append(
                f"Coordinate protein sequence is not an ordered subsequence of SEQRES for chain {chain!r}."
            )
        if consistent and protein_names:
            declared_protein_lengths[chain] = length
        summaries[chain] = {
            "record_count": len(rows),
            "declared_length": length,
            "record_residue_count": len(names),
            "declaration_consistent": consistent,
            "all_names_standard_or_caller_alias_amino_acids": protein_names,
            "observed_protein_residue_count": observed,
            "coordinate_sequence_is_ordered_subsequence": subsequence,
            "unobserved_declared_protein_residue_count": (
                length - observed if subsequence is True else None
            ),
        }
    missing = sorted(set(data["observed_protein_chain_lengths"]) - set(records))
    warnings = list(errors)
    if missing:
        warnings.append(
            "Protein coordinate chains lack SEQRES: "
            + repr(missing)
            + ". Coordinate-only loaders may omit unresolved sequence residues."
        )
    for chain, summary in summaries.items():
        if summary["unobserved_declared_protein_residue_count"]:
            warnings.append(
                f"SEQRES for chain {chain!r} includes residues without protein coordinates; "
                "verify the downstream parser preserves the intended full sequence."
            )
    expected_match = (
        None if expected is None or errors else declared_protein_lengths == expected
    )
    if expected_match is False:
        warnings.append(
            "Declared protein SEQRES chain lengths do not match the expected mapping."
        )
    data["warnings"].extend(warnings)
    return {
        "seqres_records_present": bool(records),
        "seqres_metadata_consistent": not errors,
        "seqres_chains": summaries,
        "declared_protein_seqres_chain_lengths": declared_protein_lengths,
        "expected_chain_lengths_match_seqres": expected_match,
        "coordinate_only_protein_chains": missing,
        "seqres_metadata_errors": errors,
    }


@register_tool("PDBInventoryTool")
class PDBInventoryTool(BaseTool):
    def run(self, arguments):
        try:
            index = arguments.get("model_index")
            index = 1 if index is None else index
            if (
                isinstance(index, bool)
                or not isinstance(index, int)
                or not 1 <= index <= 10000
            ):
                raise ValueError("model_index must be an integer from 1 to 10000")
            detail_limit = arguments.get("max_residue_details")
            detail_limit = 100 if detail_limit is None else detail_limit
            if (
                isinstance(detail_limit, bool)
                or not isinstance(detail_limit, int)
                or not 0 <= detail_limit <= 1000
            ):
                raise ValueError(
                    "max_residue_details must be an integer from 0 to 1000"
                )
            aliases = arguments.get("protein_residue_aliases")
            aliases = {} if aliases is None else aliases
            if not isinstance(aliases, dict):
                raise ValueError("protein_residue_aliases must be an object")
            if any(
                not isinstance(k, str)
                or not re.fullmatch(r"[A-Za-z0-9]{1,3}", k)
                or not isinstance(v, str)
                or v.upper() not in AA
                or k.upper() in AA
                and k.upper() != v.upper()
                for k, v in aliases.items()
            ):
                raise ValueError(
                    "Aliases must map nonstandard 1-3 character names to standard amino acids"
                )
            aliases = {k.upper(): v.upper() for k, v in aliases.items()}
            names = arguments.get("glycan_residue_names")
            names = [] if names is None else names
            if (
                not isinstance(names, list)
                or len(names) > 200
                or any(
                    not isinstance(n, str) or not re.fullmatch(r"[A-Za-z0-9]{1,3}", n)
                    for n in names
                )
            ):
                raise ValueError(
                    "glycan_residue_names must contain at most 200 PDB residue names"
                )
            glycans = GLYCAN_NAMES | {n.upper() for n in names}
            if glycans & (set(AA) | set(aliases)):
                raise ValueError("Protein and glycan residue classifications overlap")
            expected = arguments.get("expected_chain_lengths")
            if expected is not None and (
                not isinstance(expected, dict)
                or not expected
                or any(
                    not isinstance(c, str)
                    or len(c) != 1
                    or isinstance(n, bool)
                    or not isinstance(n, int)
                    or not 1 <= n <= 100000
                    for c, n in expected.items()
                )
            ):
                raise ValueError(
                    "expected_chain_lengths must map one-character chains to positive integer lengths"
                )
            content, kind, digest = read_input(arguments)
            models = model_records(content)
            if index > len(models):
                raise ValueError("model_index exceeds the number of input models")
            serial, lines = models[index - 1]
            data = inspect(lines, aliases, glycans, expected, detail_limit)
            data.update(inspect_seqres(content, data, aliases, expected))
            data.update(
                input_kind=kind,
                input_sha256=digest,
                input_model_count=len(models),
                selected_model_index=index,
                selected_model_serial=serial,
                protein_residue_aliases=aliases,
            )
            if len(models) > 1:
                data["warnings"].append(
                    "Only the selected model was inventoried; models were not pooled."
                )
            return {"status": "success", "data": data}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}
