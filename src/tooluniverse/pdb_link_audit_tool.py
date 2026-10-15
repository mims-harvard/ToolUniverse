"""Compare explicit legacy-PDB LINK distances locally, without inferring bonds."""

import hashlib
import math
from pathlib import Path

from .base_tool import BaseTool
from .pdb_inventory_tool import MAX_BYTES, model_records
from .tool_registry import register_tool


def _read(arguments, prefix):
    keys = [prefix + "_pdb_path", prefix + "_pdb_content"]
    supplied = [key for key in keys if arguments.get(key) is not None]
    if len(supplied) != 1:
        raise ValueError(f"Provide exactly one of {keys[0]} or {keys[1]}")
    key = supplied[0]
    value = arguments[key]
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a nonempty string")
    if key.endswith("_path"):
        with Path(value).expanduser().open("rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
    else:
        raw = value.encode("utf-8")
    if len(raw) > MAX_BYTES:
        raise ValueError("Each PDB is limited to 4 MiB")
    return raw.decode("utf-8"), hashlib.sha256(raw).hexdigest()


def _atoms(content, index):
    if isinstance(index, bool) or not isinstance(index, int) or index < 1:
        raise ValueError("Model indices must be positive integers")
    models = model_records(content)
    if index > len(models):
        raise ValueError("Requested model is absent")
    atoms = {}
    for line in models[index - 1][1]:
        if line[:6] not in ("ATOM  ", "HETATM"):
            continue
        if len(line) < 54:
            raise ValueError("Truncated coordinate record")
        xyz = tuple(float(line[i : i + 8]) for i in (30, 38, 46))
        if not all(math.isfinite(x) for x in xyz):
            raise ValueError("Nonfinite atom coordinate")
        key = (line[21], int(line[22:26]), line[26:27].strip(), line[12:16].strip())
        atoms.setdefault(key, []).append(
            {
                "altloc": line[16:17].strip(),
                "residue_name": line[17:20].strip(),
                "xyz": xyz,
            }
        )
    return atoms


def _endpoint(line, second=False):
    offset = 30 if second else 0
    return {
        "chain": line[21 + offset],
        "residue": int(line[22 + offset : 26 + offset]),
        "insertion_code": line[26 + offset : 27 + offset].strip(),
        "atom": line[12 + offset : 16 + offset].strip(),
        "altloc": line[16 + offset : 17 + offset].strip(),
        "residue_name": line[17 + offset : 20 + offset].strip(),
    }


def _key(endpoint):
    return (
        endpoint["chain"],
        endpoint["residue"],
        endpoint["insertion_code"],
        endpoint["atom"],
    )


def _resolve(atoms, endpoint):
    values = atoms.get(_key(endpoint), [])
    if endpoint["altloc"]:
        values = [v for v in values if v["altloc"] == endpoint["altloc"]]
    if len(values) != 1:
        return None, "missing_atom" if not values else "ambiguous_atom_or_altloc"
    if values[0]["residue_name"] != endpoint["residue_name"]:
        return None, "residue_name_mismatch"
    return values[0]["xyz"], None


def _compare(arguments):
    reference, reference_sha = _read(arguments, "reference")
    observed, observed_sha = _read(arguments, "observed")
    ra = _atoms(
        reference,
        (
            1
            if arguments.get("reference_model_index") is None
            else arguments["reference_model_index"]
        ),
    )
    oa = _atoms(
        observed,
        (
            1
            if arguments.get("observed_model_index") is None
            else arguments["observed_model_index"]
        ),
    )
    tolerance = arguments.get("max_length_error_angstrom")
    tolerance = 0.3 if tolerance is None else tolerance
    if isinstance(tolerance, bool) or not isinstance(tolerance, (float, int)):
        raise ValueError("Length tolerance must be numeric")
    if not math.isfinite(tolerance) or not 0 <= tolerance <= 10:
        raise ValueError(
            "Length tolerance must be finite and between 0 and 10 Angstrom"
        )
    chain_map = {} if arguments.get("chain_map") is None else arguments["chain_map"]
    if not isinstance(chain_map, dict) or any(
        not isinstance(k, str) or len(k) != 1 or not isinstance(v, str) or len(v) != 1
        for k, v in chain_map.items()
    ):
        raise ValueError("chain_map keys and values must be one-character chain IDs")
    residue_map = {}
    mapping_rows = arguments.get("residue_map")
    mapping_rows = [] if mapping_rows is None else mapping_rows
    if not isinstance(mapping_rows, list) or len(mapping_rows) > 10000:
        raise ValueError("residue_map must be an array with at most 10000 rows")
    for row in mapping_rows:
        if not isinstance(row, dict):
            raise ValueError("Each residue mapping must be an object")
        chain = row.get("reference_chain")
        numbers = [row.get(k) for k in ("reference_residue", "observed_residue")]
        codes = [
            row.get(k, "")
            for k in ("reference_insertion_code", "observed_insertion_code")
        ]
        if (
            not isinstance(chain, str)
            or len(chain) != 1
            or any(isinstance(n, bool) or not isinstance(n, int) for n in numbers)
            or any(not isinstance(c, str) or len(c) > 1 for c in codes)
        ):
            raise ValueError("Invalid explicit residue mapping")
        key = (chain, numbers[0], codes[0])
        if key in residue_map:
            raise ValueError("Duplicate source residue mapping")
        residue_map[key] = (numbers[1], codes[1])
    links, seen, targets = [], set(), {}
    for number, line in enumerate(reference.splitlines(), 1):
        if line[:6] != "LINK  ":
            continue
        if len(line) < 57:
            raise ValueError(f"Truncated LINK at line {number}")
        if any(s.strip() not in ("", "1555") for s in (line[59:65], line[66:72])):
            raise ValueError(
                "Symmetry-transformed LINKs require crystallographic expansion"
            )
        endpoints = [_endpoint(line), _endpoint(line, True)]
        identity = tuple(sorted((_key(e), e["altloc"]) for e in endpoints))
        if identity in seen:
            raise ValueError("Duplicate reference LINK declaration")
        seen.add(identity)
        if identity[0] == identity[1]:
            raise ValueError("Self LINK declaration")
        mapped = []
        for e in endpoints:
            dest = dict(e, chain=chain_map.get(e["chain"], e["chain"]))
            dest["residue"], dest["insertion_code"] = residue_map.get(
                (e["chain"], e["residue"], e["insertion_code"]),
                (e["residue"], e["insertion_code"]),
            )
            source_key = (_key(e), e["altloc"])
            dest_key = (_key(dest), dest["altloc"])
            if dest_key in targets and targets[dest_key] != source_key:
                raise ValueError("Mapping collapses distinct reference atoms")
            targets[dest_key] = source_key
            mapped.append(dest)
        row = {
            "reference_endpoints": endpoints,
            "observed_endpoints": mapped,
            "reference_length_angstrom": None,
            "observed_length_angstrom": None,
            "absolute_length_error_angstrom": None,
            "distance_agreement": False,
        }
        reference_points = [_resolve(ra, e) for e in endpoints]
        observed_points = [_resolve(oa, e) for e in mapped]
        errors = [
            f"{kind}_endpoint_{i + 1}:{err}"
            for kind, values in (
                ("reference", reference_points),
                ("observed", observed_points),
            )
            for i, (_, err) in enumerate(values)
            if err
        ]
        if errors:
            row["resolution_errors"] = errors
        else:
            ref_length = math.dist(*(v[0] for v in reference_points))
            obs_length = math.dist(*(v[0] for v in observed_points))
            if not math.isfinite(ref_length) or not math.isfinite(obs_length):
                raise ValueError("Nonfinite LINK distance")
            error = abs(obs_length - ref_length)
            row.update(
                reference_length_angstrom=ref_length,
                observed_length_angstrom=obs_length,
                absolute_length_error_angstrom=error,
                distance_agreement=error <= tolerance,
            )
        links.append(row)
        if len(links) > 10000:
            raise ValueError("At most 10000 reference LINK declarations are supported")
    if not links:
        raise ValueError(
            "Reference has no explicit LINK declarations; bonds are never inferred"
        )
    errors = [
        r["absolute_length_error_angstrom"]
        for r in links
        if r["absolute_length_error_angstrom"] is not None
    ]
    return {
        "reference_sha256": reference_sha,
        "observed_sha256": observed_sha,
        "reference_link_count": len(links),
        "resolved_link_count": len(errors),
        "unresolved_link_count": len(links) - len(errors),
        "max_length_error_angstrom": max(errors) if errors else None,
        "all_declared_distances_agree": len(errors) == len(links)
        and all(r["distance_agreement"] for r in links),
        "max_allowed_length_error_angstrom": tolerance,
        "links": links,
        "chemical_validation": False,
        "limitations": [
            "Explicit LINK distance comparison only; no bond inference, SSBOND/CONECT, chemistry, stereochemistry or binding validation.",
            "Reference geometry is not assumed correct. Caller must explicitly map renumbered residues/chains. Alternate locations are not chosen by occupancy.",
        ],
    }


@register_tool("PDBLinkAuditTool")
class PDBLinkAuditTool(BaseTool):
    def run(self, arguments):
        try:
            return {"status": "success", "data": _compare(arguments)}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}
