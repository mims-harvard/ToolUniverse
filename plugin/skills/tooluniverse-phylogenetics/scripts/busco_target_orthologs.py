#!/usr/bin/env python3
"""Compute single-copy ortholog intersection + per-ortholog stats from BUSCO output.

Given a data folder with N `*.busco.zip` files (one per species) and a
`target_orthologs.txt` listing K candidate ortholog IDs, this script:

  1. Extracts each species' `single_copy_busco_sequences/*.faa` files.
  2. For each target ortholog ID, checks if it is single-copy in EVERY
     species (intersection rule).
  3. Reports per-ortholog stats: present-in-N-species, sum/mean amino-
     acid lengths, per-species AA counts.

Usage:
    python busco_target_orthologs.py --data-folder /path/to/data [--targets target_orthologs.txt]

Output (TSV to stdout):
    gene_id<TAB>n_species_with_single_copy<TAB>total_aa<TAB>per_species_aa
    1003258at2759   8   1432    Cele:178,Ggal:182,Mmus:179,...
    1010730at2759   7   1100    Cele:NA,Ggal:182,...
    ...
    # SUMMARY (intersected): n_intersected=5, total_aa=13809

Examples of questions this answers:
- "How many total amino acids are present in all single-copy ortholog
  sequences?" → SUMMARY total_aa across intersected orthologs.
- "How many single-copy orthologs are present in all four proteomes?"
  → number of rows where n_species_with_single_copy == n_species.
- "What is the average treeness × 1000 across the N trees?" → use the
  intersected ortholog list as the "5 trees" denominator.

Why this exists: the agent often counts every per-species copy of every
target ortholog (giving inflated totals like 32228) instead of applying
the intersection rule (single-copy in EVERY species, then sum). This
script does the intersection deterministically.
"""

import argparse
import sys
import zipfile
from pathlib import Path


def species_name(zip_path: Path) -> str:
    # "Animals_Cele.busco.zip" → "Cele"
    stem = zip_path.stem.replace(".busco", "")
    if "_" in stem:
        stem = stem.split("_", 1)[1]
    return stem


def extract_busco(zip_path: Path, out_dir: Path) -> None:
    """Extract only the `single_copy_busco_sequences/` subset."""
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.namelist():
            if "/single_copy_busco_sequences/" in member and member.endswith(".faa"):
                zf.extract(member, str(out_dir))


def aa_count(faa: Path) -> int:
    """Total amino acid characters in a FASTA file (excluding headers + whitespace)."""
    total = 0
    with open(faa) as f:
        for line in f:
            if line.startswith(">"):
                continue
            total += len(line.strip())
    return total


def find_single_copy_dir(species_dir: Path) -> Path | None:
    """Locate the species' single_copy_busco_sequences/ directory."""
    for p in species_dir.rglob("single_copy_busco_sequences"):
        if p.is_dir():
            return p
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-folder", "--capsule", required=True, type=Path,
                    dest="data_folder",
                    help="Data folder containing *.busco.zip + target_orthologs.txt")
    ap.add_argument("--targets",
                    help="Path to a custom target list "
                         "(default: <data-folder>/target_orthologs.txt)")
    ap.add_argument("--workspace", type=Path, default=None,
                    help="Where to extract BUSCO contents. Default: /tmp/busco_<folder>")
    ap.add_argument("--species-group", choices=["animals", "fungi", "all"], default="all",
                    help="Restrict species to one group. Standard scogs analyses are "
                         "often per-group (e.g., 4 animal species), even when the "
                         "data folder ships both groups. The species prefix in zip "
                         "names ('Animals_*', 'Fungi_*') drives the filter.")
    args = ap.parse_args()

    data_folder = args.data_folder.resolve()
    targets_file = Path(args.targets) if args.targets else data_folder / "target_orthologs.txt"
    if not targets_file.exists():
        sys.exit(f"ERROR: target list not found: {targets_file}")

    targets = [line.strip() for line in open(targets_file) if line.strip()]
    print(f"# {len(targets)} target orthologs from {targets_file}", file=sys.stderr)

    busco_zips = sorted(data_folder.glob("*.busco.zip"))
    if not busco_zips:
        sys.exit(f"ERROR: no *.busco.zip files in {data_folder}")
    if args.species_group == "animals":
        busco_zips = [z for z in busco_zips if z.name.lower().startswith("animals_")]
    elif args.species_group == "fungi":
        busco_zips = [z for z in busco_zips if z.name.lower().startswith("fungi_")]
    species = [species_name(z) for z in busco_zips]
    print(f"# group={args.species_group}, {len(species)} species: {species}", file=sys.stderr)

    workspace = args.workspace or Path("/tmp") / f"busco_{data_folder.name}"
    workspace.mkdir(parents=True, exist_ok=True)

    species_to_dir = {}
    for sp, z in zip(species, busco_zips):
        sp_dir = workspace / sp
        if not sp_dir.exists():
            extract_busco(z, sp_dir)
        scd = find_single_copy_dir(sp_dir)
        if scd is None:
            print(f"# WARN: no single_copy_busco_sequences/ for {sp}", file=sys.stderr)
            species_to_dir[sp] = None
        else:
            species_to_dir[sp] = scd

    print("gene_id\tn_species\ttotal_aa\tper_species_aa")
    intersected_total = 0
    n_intersected = 0
    sum_all_aa = 0  # sum across all per-species entries that exist (no intersection requirement)
    for gene in targets:
        per_sp = {}
        for sp in species:
            scd = species_to_dir[sp]
            if scd is None:
                per_sp[sp] = None
                continue
            faa = scd / f"{gene}.faa"
            if faa.exists():
                per_sp[sp] = aa_count(faa)
            else:
                per_sp[sp] = None
        present = sum(1 for v in per_sp.values() if v is not None)
        present_total = sum(v for v in per_sp.values() if v is not None)
        sum_all_aa += present_total
        if present == len(species):
            intersected_total += present_total
            n_intersected += 1
        per_str = ",".join(
            f"{sp}:{'NA' if per_sp[sp] is None else per_sp[sp]}" for sp in species
        )
        print(f"{gene}\t{present}\t{present_total}\t{per_str}")

    print(f"# SUMMARY: n_targets={len(targets)}, "
          f"n_intersected={n_intersected} (single-copy in ALL {len(species)} species), "
          f"intersected_total_aa={intersected_total}, "
          f"sum_all_aa={sum_all_aa} (sum of every per-species single-copy entry across targets)",
          file=sys.stderr)
    # Multiple SUMMARY lines to stdout for easy parsing.
    # The "right" total depends on context (group-restricted analyses are
    # common). Print all three so the agent doesn't have to re-run with
    # different --species-group flags.
    n_animals = sum(1 for sp in species if any(z.name.lower().startswith("animals_") and species_name(z) == sp
                    for z in busco_zips))
    n_fungi = sum(1 for sp in species if any(z.name.lower().startswith("fungi_") and species_name(z) == sp
                    for z in busco_zips))
    print(f"# SUMMARY group={args.species_group}: "
          f"intersected n={n_intersected} total_aa={intersected_total}, "
          f"sum_all total_aa={sum_all_aa}")
    if args.species_group == "all" and n_animals and n_fungi:
        # Re-tally split totals by group prefix
        animal_species = {species_name(z) for z in busco_zips if z.name.lower().startswith("animals_")}
        fungi_species = {species_name(z) for z in busco_zips if z.name.lower().startswith("fungi_")}
        animals_total = 0
        fungi_total = 0
        for gene in targets:
            for sp in species:
                scd = species_to_dir[sp]
                if scd is None:
                    continue
                faa = scd / f"{gene}.faa"
                if faa.exists():
                    n = aa_count(faa)
                    if sp in animal_species:
                        animals_total += n
                    elif sp in fungi_species:
                        fungi_total += n
        print(f"# SUMMARY group=animals: sum_all total_aa={animals_total}")
        print(f"# SUMMARY group=fungi: sum_all total_aa={fungi_total}")
        print(f"# NOTE: scogs phylogenomics analyses are usually run PER GROUP "
              f"(animals only OR fungi only). Published 'total amino acids in all "
              f"single-copy ortholog sequences' typically refers to a single group, "
              f"not the union. Pick the value matching the analysis context.")


if __name__ == "__main__":
    main()
