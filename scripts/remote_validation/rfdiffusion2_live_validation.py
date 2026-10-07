#!/usr/bin/env python3
"""End-to-end validation of a live RFdiffusion2 remote-tool deployment.

Connects through ToolUniverse the way a user does, checks discovery and the
input boundaries, runs one real enzyme active-site design (the upstream
``active_site_unindexed_atomic`` demo: lactate dehydrogenase 1LDM with NAD and
oxamate), and re-parses the returned PDB independently of the provider's own
checks. The design and a JSON report are written to ``--out``.

The provider must serve RFdiffusion2's ``rf_diffusion/benchmark/input`` as
``RFDIFFUSION2_INPUT_ROOT``. Pass the same ``mcsa_41/M0584_1ldm.pdb`` as
``--reference-pdb`` to also measure how closely the design reproduces the
active-site atoms.

    export RFDIFFUSION2_MCP_SERVER_HOST=127.0.0.1
    python scripts/remote_validation/rfdiffusion2_live_validation.py --out out
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import sys
from pathlib import Path

import numpy as np

TOOL = "mcp_rfdiffusion2_design"
MOTIF = {"A106": "NE,CD,CZ", "A166": "OD1,CG", "A169": "NH2,CZ", "A193": "NE2,CD2,CE1"}
DESIGN = {
    "contig_map": "46,A106-106,59,A166-166,2,A169-169,23,A193-193,46",
    "input_pdb": "mcsa_41/M0584_1ldm.pdb",
    "ligand": "NAD,OXM",
    "contig_atoms": MOTIF,
    "contig_as_guidepost": True,
    "num_designs": 1,
    "seed": 43,
}
EXPECTED_RESIDUES = 180
EXPECTED_LIGANDS = ["NAD", "OXM"]
EXPECTED_MOTIF_NAMES = ["ARG", "ARG", "ASP", "HIS"]


def parse_pdb(text):
    """Return {(chain, number): (residue name, {atom: xyz})} and ligand atoms."""
    residues, ligands = {}, {}
    for line in text.splitlines():
        record = line[:6].strip()
        if record not in ("ATOM", "HETATM"):
            continue
        xyz = (float(line[30:38]), float(line[38:46]), float(line[46:54]))
        if record == "HETATM":
            ligands.setdefault(line[17:20].strip(), []).append(xyz)
            continue
        key = (line[21].strip(), line[22:27].strip())
        residues.setdefault(key, (line[17:20].strip(), {}))[1][line[12:16].strip()] = (
            xyz
        )
    return residues, ligands


def kabsch_rmsd(mobile, target):
    mobile, target = np.asarray(mobile), np.asarray(target)
    mobile_centered = mobile - mobile.mean(axis=0)
    target_centered = target - target.mean(axis=0)
    u, _, vt = np.linalg.svd(mobile_centered.T @ target_centered)
    sign = np.sign(np.linalg.det(u @ vt))
    rotation = u @ np.diag([1.0, 1.0, sign]) @ vt
    return float(
        np.sqrt(
            ((mobile_centered @ rotation - target_centered) ** 2).sum(axis=1).mean()
        )
    )


def motif_rmsd(design_residues, reference_text):
    """Best-superposition RMSD of the motif atoms, trying every assignment of
    design residues to same-named reference residues (guideposts let the model
    choose the sequence positions)."""
    reference, _ = parse_pdb(reference_text)
    wanted = [
        (
            reference[(key[0], key[1:])][0],
            atoms.split(","),
            reference[(key[0], key[1:])][1],
        )
        for key, atoms in MOTIF.items()
    ]
    candidates = [
        entry
        for entry in design_residues.values()
        if set(entry[1]) - {"N", "CA", "C", "O", "CB", "OXT"}
    ]
    best = math.inf
    for order in itertools.permutations(candidates, len(wanted)):
        if any(have[0] != want[0] for have, want in zip(order, wanted)):
            continue
        try:
            mobile = [have[1][a] for have, want in zip(order, wanted) for a in want[1]]
        except KeyError:
            continue
        target = [want[2][a] for want in wanted for a in want[1]]
        best = min(best, kabsch_rmsd(mobile, target))
    return best


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, default=Path("rfdiffusion2_validation"))
    parser.add_argument("--reference-pdb", type=Path)
    options = parser.parse_args()
    options.out.mkdir(parents=True, exist_ok=True)

    from tooluniverse import ToolUniverse

    tu = ToolUniverse()
    tu.load_tools(categories=["mcp_auto_loader_rfdiffusion2"])
    checks = {}

    def call(arguments):
        return tu.run({"name": TOOL, "arguments": arguments})

    def rejected(arguments):
        result = call(arguments)
        return isinstance(result, dict) and result.get("status") == "error"

    config = tu.all_tool_dict.get(TOOL, {})
    checks["discovered"] = config.get("type") == "MCPProxyTool"
    checks["closed_input_schema"] = (
        config.get("parameter", {}).get("additionalProperties") is False
    )
    # Each probe changes one field of a request that is otherwise valid, so a
    # rejection can only come from the boundary under test.
    dry = call({**DESIGN, "dry_run": True})
    checks["dry_run"] = (
        dry.get("status") == "success"
        and f"contigmap.contigs=['{DESIGN['contig_map']}']" in dry["data"]["overrides"]
    )
    checks["rejects_path_outside_input_root"] = rejected(
        {**DESIGN, "input_pdb": "/etc/passwd", "dry_run": True}
    ) and rejected({**DESIGN, "input_pdb": "../../etc/passwd.pdb", "dry_run": True})
    checks["dry_run_rejects_missing_input"] = rejected(
        {**DESIGN, "input_pdb": "no_such_file.pdb", "dry_run": True}
    )
    checks["rejects_unknown_argument"] = rejected(
        {**DESIGN, "extra_args": ["hydra.run.dir=/tmp/x"], "dry_run": True}
    )
    checks["rejects_override_injection"] = rejected(
        {
            **DESIGN,
            "contig_map": "150'] inference.output_prefix=/tmp/x",
            "dry_run": True,
        }
    )
    checks["rejects_out_of_range"] = rejected(
        {**DESIGN, "num_designs": 99, "dry_run": True}
    )

    result = call(DESIGN)
    report = {"checks": checks, "tool": TOOL, "arguments": DESIGN}
    checks["design_succeeded"] = result.get("status") == "success"
    if checks["design_succeeded"]:
        data = result["data"]
        design = data["designs"][0]
        pdb_text = design.pop("pdb")
        (options.out / f"{design['name']}.pdb").write_text(pdb_text, encoding="utf-8")
        residues, ligands = parse_pdb(pdb_text)
        ca = [atoms["CA"] for _, atoms in residues.values()]
        ca_steps = [math.dist(a, b) for a, b in zip(ca, ca[1:])]
        motif_names = sorted(
            name
            for name, atoms in residues.values()
            if set(atoms) - {"N", "CA", "C", "O", "CB", "OXT"}
        )
        checks["one_design_returned"] = data["num_designs"] == 1
        checks["residue_count"] = (
            len(residues) == EXPECTED_RESIDUES == design["num_residues"]
        )
        checks["ligands_present"] = (
            sorted(ligands) == EXPECTED_LIGANDS == design["ligands"]
        )
        checks["motif_side_chains_present"] = motif_names == EXPECTED_MOTIF_NAMES
        checks["coordinates_finite"] = all(math.isfinite(v) for xyz in ca for v in xyz)
        checks["chain_is_connected"] = all(3.6 < step < 4.0 for step in ca_steps)
        report["design"] = design
        report["runtime_seconds"] = data["runtime_seconds"]
        report["ca_ca_distance_range"] = [
            round(min(ca_steps), 3),
            round(max(ca_steps), 3),
        ]
        if options.reference_pdb:
            rmsd = motif_rmsd(
                residues, options.reference_pdb.read_text(encoding="utf-8")
            )
            report["motif_atom_rmsd_angstrom"] = round(rmsd, 3)
            checks["motif_geometry_reproduced"] = rmsd < 1.0
    else:
        report["error"] = result.get("error")

    report["passed"] = all(checks.values())
    (options.out / "report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
