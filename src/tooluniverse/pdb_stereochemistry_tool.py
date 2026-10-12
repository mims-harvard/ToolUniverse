"""Local C-alpha orientation checks; distances cannot detect a reflection."""

import math
import re
from collections import Counter
from typing import Any, Dict, List, Tuple

from .base_tool import BaseTool
from .pdb_inventory_tool import AA, element, model_records, read_input
from .tool_registry import register_tool


def signed_determinant(points: List[Tuple[float, float, float]]) -> float:
    """det(N-CA, C-CA, CB-CA), in A^3; positive for L orientation.

    This atom ordering is a geometric convention, not CIP R/S assignment.
    Cysteine uses the same convention despite its different CIP priorities.
    """
    center, nitrogen, carbonyl, beta = points
    u, v, w = [
        tuple(a - b for a, b in zip(p, center)) for p in (nitrogen, carbonyl, beta)
    ]
    return (
        u[0] * (v[1] * w[2] - v[2] * w[1])
        - u[1] * (v[0] * w[2] - v[2] * w[0])
        + u[2] * (v[0] * w[1] - v[1] * w[0])
    )


def inspect_centers(
    lines: List[str],
    aliases: Dict[str, str],
    expected: str,
    epsilon: float,
    minimum_normalized_volume: float,
    limit: int,
) -> Dict[str, Any]:
    residues: Dict[Tuple[Any, ...], Dict[str, Any]] = {}
    segments: Counter = Counter()
    for line in lines:
        record = line[:6]
        if record == "TER   ":
            segments[line[21:22] or " "] += 1
            continue
        if record not in ("ATOM  ", "HETATM"):
            continue
        if len(line) < 54:
            raise ValueError("Truncated PDB coordinate record")
        name, chain = line[17:20].strip().upper(), line[21]
        number, insertion = int(line[22:26]), line[26:27].strip()
        key = chain, segments[chain], number, insertion
        residue = residues.setdefault(key, {"names": set(), "atoms": {}})
        residue["names"].add(name)
        atom = line[12:16].strip()
        if atom not in ("CA", "N", "C", "CB"):
            continue
        xyz = tuple(float(line[i : i + 8]) for i in (30, 38, 46))
        if not all(math.isfinite(x) for x in xyz):
            raise ValueError("Nonfinite center coordinates")
        symbol, _ = element(line)
        residue["atoms"].setdefault(atom, []).append(
            {"alt": line[16].strip(), "xyz": xyz, "element": symbol}
        )
    counts: Counter = Counter()
    chain_counts: Dict[str, Counter] = {}
    details = []
    issues = []
    for key, residue in residues.items():
        chain, segment, number, insertion = key
        names = residue["names"]
        canonical = {aliases.get(n, n) for n in names}
        protein = bool(canonical & set(AA))
        # An unrecognized backbone-like residue cannot silently count as checked.
        backbone_like = {"N", "CA", "C"} <= set(residue["atoms"])
        if not protein and not backbone_like:
            continue
        identity = {
            "chain": chain,
            "segment_index": segment,
            "residue_number": number,
            "insertion_code": insertion,
            "residue_names": sorted(names),
        }
        counts["coordinate_protein_like_residues"] += 1
        if len(canonical) != 1 or not protein:
            counts["uncheckable_centers"] += 1
            issues.append(
                dict(identity, reason="Unrecognized or conflicting residue identity")
            )
            continue
        residue_name = next(iter(canonical))
        if residue_name == "GLY":
            counts["glycine_nonchiral_residues"] += 1
            continue
        atoms = residue["atoms"]
        alts = sorted(
            {a["alt"] for values in atoms.values() for a in values if a["alt"]}
        ) or [""]
        for alt in alts:
            selected = []
            error = None
            for name in ("CA", "N", "C", "CB"):
                specific = [a for a in atoms.get(name, []) if a["alt"] == alt]
                shared = [a for a in atoms.get(name, []) if not a["alt"]]
                candidates = specific or shared
                if len(candidates) != 1:
                    error = "Missing or ambiguous " + name
                    break
                value = candidates[0]
                if value["element"] != ("N" if name == "N" else "C"):
                    error = "Unexpected element for " + name
                    break
                selected.append(value["xyz"])
            row = dict(
                identity, canonical_residue_name=residue_name, alternate_location=alt
            )
            if error:
                counts["uncheckable_centers"] += 1
                issues.append(dict(row, reason=error))
                continue
            determinant = signed_determinant(selected)
            if not math.isfinite(determinant):
                raise ValueError("Nonfinite center determinant")
            lengths = [
                math.sqrt(sum((a - b) ** 2 for a, b in zip(p, selected[0])))
                for p in selected[1:]
            ]
            denominator = math.prod(lengths)
            normalized = determinant / denominator if denominator else None
            degenerate = (
                abs(determinant) <= epsilon
                or normalized is None
                or abs(normalized) < minimum_normalized_volume
            )
            orientation = (
                "degenerate" if degenerate else ("L" if determinant > 0 else "D")
            )
            match = orientation == expected
            counts["checked_centers"] += 1
            counts[
                "matched_centers" if match else "opposite_or_degenerate_centers"
            ] += 1
            chain_counts.setdefault(chain, Counter())[orientation] += 1
            row.update(
                determinant_A3=determinant,
                normalized_determinant=normalized,
                orientation=orientation,
                matches_expected=match,
            )
            if not match:
                issues.append(row)
            if len(details) < limit:
                details.append(row)
    checked = counts["checked_centers"]
    complete = bool(checked and not counts["uncheckable_centers"])
    return {
        **{
            key: counts[key]
            for key in (
                "coordinate_protein_like_residues",
                "glycine_nonchiral_residues",
                "checked_centers",
                "matched_centers",
                "opposite_or_degenerate_centers",
                "uncheckable_centers",
            )
        },
        "complete_coordinate_center_coverage": complete,
        "all_checked_centers_match": (not counts["opposite_or_degenerate_centers"])
        if checked
        else None,
        "all_coordinate_centers_match_expected": (
            complete and not counts["opposite_or_degenerate_centers"]
        ),
        "counts_by_chain": {key: dict(value) for key, value in chain_counts.items()},
        "center_details": details,
        "center_details_truncated": checked > len(details),
        "issues": issues[:limit],
        "issue_count": len(issues),
        "issues_truncated": len(issues) > limit,
    }


@register_tool("PDBStereochemistryTool")
class PDBStereochemistryTool(BaseTool):
    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            index = arguments.get("model_index")
            index = 1 if index is None else index
            limit = arguments.get("max_residue_details")
            limit = 100 if limit is None else limit
            if (
                isinstance(index, bool)
                or not isinstance(index, int)
                or not 1 <= index <= 10000
            ):
                raise ValueError("model_index must be an integer from 1 to 10000")
            if (
                isinstance(limit, bool)
                or not isinstance(limit, int)
                or not 0 <= limit <= 1000
            ):
                raise ValueError(
                    "max_residue_details must be an integer from 0 to 1000"
                )
            expected = arguments.get("expected_orientation") or "L"
            if expected not in ("L", "D"):
                raise ValueError("expected_orientation must be L or D")
            epsilon = arguments.get("degenerate_tolerance_A3")
            epsilon = 1e-6 if epsilon is None else epsilon
            if (
                isinstance(epsilon, bool)
                or not isinstance(epsilon, (int, float))
                or not math.isfinite(epsilon)
                or not 0 <= epsilon <= 0.1
            ):
                raise ValueError("degenerate_tolerance_A3 must be finite from 0 to 0.1")
            normalized = arguments.get("minimum_normalized_volume")
            normalized = 0.1 if normalized is None else normalized
            if (
                isinstance(normalized, bool)
                or not isinstance(normalized, (int, float))
                or not math.isfinite(normalized)
                or not 0 <= normalized <= 1
            ):
                raise ValueError("minimum_normalized_volume must be finite from 0 to 1")
            aliases = arguments.get("protein_residue_aliases")
            aliases = {} if aliases is None else aliases
            if not isinstance(aliases, dict) or any(
                not isinstance(k, str)
                or not re.fullmatch(r"[A-Za-z0-9]{1,3}", k)
                or not isinstance(v, str)
                or v.upper() not in AA
                or k.upper() in AA
                and k.upper() != v.upper()
                for k, v in aliases.items()
            ):
                raise ValueError(
                    "Aliases must map nonstandard names to canonical amino acids"
                )
            aliases = {k.upper(): v.upper() for k, v in aliases.items()}
            content, kind, digest = read_input(arguments)
            models = model_records(content)
            if not models or index > len(models):
                raise ValueError("Requested model does not exist")
            data = inspect_centers(
                models[index - 1][1], aliases, expected, epsilon, normalized, limit
            )
            data.update(
                input_sha256=digest,
                input_source=kind,
                input_model_count=len(models),
                selected_model_index=index,
                selected_model_serial=models[index - 1][0],
                expected_orientation=expected,
                degenerate_tolerance_A3=epsilon,
                minimum_normalized_volume=normalized,
                protein_residue_aliases=aliases,
                binding_verified=False,
                pH_selectivity_verified=False,
                structure_chemistry_verified=False,
                scope="C-alpha N/CA/C/CB orientation only; not CIP R/S, Ile/Thr sidechain chirality, complete stereochemistry, energy or binding validation. Coverage is coordinate-only; SEQRES omissions are not assessed.",
            )
            return {"status": "success", "data": data}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}
