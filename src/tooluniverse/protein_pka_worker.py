"""Isolated PROPKA worker; no ToolUniverse or optional imports at module load."""

import io
import json
import logging
import math
import sys
from importlib.metadata import version
from pathlib import Path

PROTEIN_GROUPS = {"HIS", "ASP", "GLU", "LYS", "ARG", "CYS", "TYR", "N+", "C-"}


def protonated_fraction(pka, ph):
    """Independent-site Henderson-Hasselbalch estimate, not a charge or affinity."""
    exponent = ph - pka
    if exponent >= 0:
        ratio = 10.0 ** (-exponent)
        return ratio / (1.0 + ratio)
    return 1.0 / (1.0 + 10.0**exponent)


def predict(path, ph_values):
    import propka.run

    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    logger = logging.getLogger("propka")
    level, propagate = logger.level, logger.propagate
    logger.addHandler(handler)
    logger.setLevel(logging.WARNING)
    logger.propagate = False
    try:
        molecule = propka.run.single(str(path), write_pka=False)
    finally:
        logger.removeHandler(handler)
        logger.setLevel(level)
        logger.propagate = propagate
    names = molecule.conformation_names
    if len(names) != 1:
        raise ValueError(
            "Expected one PROPKA conformation; select one input model/altloc"
        )
    groups, omitted = [], []
    for group in molecule.conformations[names[0]].groups:
        if group.type not in PROTEIN_GROUPS:
            continue
        atom = group.atom
        row = {
            "chain": atom.chain_id,
            "residue_number": int(atom.res_num),
            "insertion_code": atom.icode.strip(),
            "group_type": group.type,
            "label": group.label,
        }
        pka = float(group.pka_value)
        if not math.isfinite(pka):
            omitted.append(row)
            continue
        groups.append(
            {
                **row,
                "pka": pka,
                "protonated_fractions": [
                    {"pH": ph, "fraction": protonated_fraction(pka, ph)}
                    for ph in ph_values
                ],
            }
        )
    if not groups:
        raise ValueError("PROPKA returned no finite protein ionization groups")
    return {
        "groups": groups,
        "omitted_nonfinite_groups": omitted,
        "conformation": names[0],
        "warnings": stream.getvalue().splitlines(),
    }


def group_key(row):
    return (
        row["chain"],
        row["residue_number"],
        row["insertion_code"],
        row["group_type"],
    )


def compare(bound, free, chain):
    bound_rows = [row for row in bound["groups"] if row["chain"] == chain]
    free_rows = {group_key(row): row for row in free["groups"]}
    matched, missing = [], []
    for row in bound_rows:
        reference = free_rows.get(group_key(row))
        if reference is None:
            missing.append(
                {
                    key: row[key]
                    for key in (
                        "chain",
                        "residue_number",
                        "insertion_code",
                        "group_type",
                    )
                }
            )
            continue
        matched.append(
            {
                **row,
                "bound_pka": row["pka"],
                "free_pka": reference["pka"],
                "bound_minus_free_pka": row["pka"] - reference["pka"],
                "free_protonated_fractions": reference["protonated_fractions"],
            }
        )
    if not matched:
        raise ValueError(
            "No matching finite ionization groups in the requested partner"
        )
    return {
        "matched_groups": matched,
        "unmatched_bound_groups": missing,
        "unmatched_free_groups": [
            row
            for key, row in free_rows.items()
            if key not in {group_key(r) for r in bound_rows}
        ],
    }


def main():
    request = json.loads(Path(sys.argv[1]).read_text())
    try:
        bound = predict(Path(request["pdb_path"]), request["ph_values"])
        data = {"prediction": bound, "propka_version": version("propka")}
        if request.get("free_path"):
            free = predict(Path(request["free_path"]), request["ph_values"])
            data.update(
                free_prediction=free,
                comparison=compare(bound, free, request["partner_chain"]),
            )
        result = {"status": "success", "data": data}
    except Exception as exc:
        result = {"status": "error", "error": str(exc)}
    Path(sys.argv[2]).write_text(json.dumps(result, allow_nan=False))


if __name__ == "__main__":
    main()
