#!/usr/bin/env python3
"""Phase 5 — batch peptide:receptor co-folding screen (structural confirmation).

Takes a peptide sequence and a shortlist of candidate receptor gene symbols
(e.g. the Tier-1/2 output of ``deorphanize_peptide.py``), fetches each receptor's
sequence, and co-folds the peptide with each receptor via NVIDIA NIM, ranking by
interface confidence (ipTM / interface pLDDT). The highest-interface candidate is
the top structurally-supported target.

Requires ``NVIDIA_API_KEY`` for the actual co-fold. Without it, the script runs a
DRY RUN: it still resolves every receptor sequence and prints the co-fold plan, so
you can verify inputs before paying for GPU time. Keep the shortlist small (<=8) —
each co-fold is minutes-scale.

Examples:
    # dry run (no key needed) — verifies inputs + prints the plan
    python3 cofold_screen.py --peptide HGEGTF...PPPS --candidates GIPR GCGR GLP2R

    # real screen (NVIDIA_API_KEY set), also co-fold the mouse ortholog of the lead
    python3 cofold_screen.py --peptide HGEGTF...PPPS --candidates GIPR GCGR \
        --backend boltz2 --assay-species mus_musculus
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional


def _load_tu():
    try:
        from tooluniverse import ToolUniverse
    except ImportError:
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src"))
        from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()
    return tu


_BACKENDS = {
    "boltz2": "NvidiaNIM_boltz2",
    "alphafold2_multimer": "NvidiaNIM_alphafold2_multimer",
    "openfold3": "NvidiaNIM_openfold3",
}

# UniProt organism filter accepts common names; map the usual species tokens.
_ORGANISM_COMMON = {
    "homo_sapiens": "human", "mus_musculus": "mouse", "rattus_norvegicus": "rat",
    "danio_rerio": "zebrafish",
}


class CoFolder:
    def __init__(self, tu):
        self.tu = tu

    def run(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            out = self.tu.run({"name": name, "arguments": args})
        except Exception as exc:
            return {"status": "error", "error": f"{type(exc).__name__}: {exc}"}
        return out if isinstance(out, dict) else {"status": "success", "data": out}

    @staticmethod
    def _data(resp):
        return resp.get("data") if isinstance(resp, dict) and resp.get("status") == "success" else None

    def _uniprot_accession(self, symbol: str) -> Optional[str]:
        g = self._data(self.run("HGNC_fetch_gene_by_symbol", {"symbol": symbol}))
        ids = (g or {}).get("uniprot_ids") if isinstance(g, dict) else None
        return ids[0] if ids else None

    def _sequence_for_accession(self, accession: Optional[str]) -> Optional[str]:
        if not accession:
            return None
        seq = self._data(self.run("UniProt_get_sequence_by_accession", {"accession": accession}))
        if isinstance(seq, str):
            return seq.strip() or None
        if isinstance(seq, dict):
            return seq.get("sequence") or seq.get("value")
        return None

    def receptor_sequence(self, symbol: str) -> Optional[str]:
        """Resolve a receptor's protein sequence (GPCRdb first, UniProt fallback).

        GPCRdb keys some receptors under alias entry-names (e.g. glucagon receptor
        is 'glr_human', not 'gcgr_human'), so fall back to the HGNC->UniProt
        accession->sequence path, which is canonical for any human protein.
        """
        gp = self._data(self.run("GPCRdb_get_protein", {"protein": symbol}))
        if isinstance(gp, dict) and gp.get("sequence"):
            return gp["sequence"]
        return self._sequence_for_accession(self._uniprot_accession(symbol))

    def ortholog_sequence(self, symbol: str, species: str) -> Optional[str]:
        """Fetch the assay-species ortholog sequence (UniProt gene+organism search).

        Canonical for any species; replaces the GPCRdb entry-name guess, whose
        species suffixes are common names ('_mouse'), not the 'mus_musculus' token.
        """
        organism = _ORGANISM_COMMON.get(species.lower(), species.replace("_", " "))
        res = self._data(self.run("UniProt_search", {"query": f"gene:{symbol}", "organism": organism, "limit": 1}))
        rows = res.get("results") if isinstance(res, dict) else None
        acc = rows[0].get("accession") if rows else None
        return self._sequence_for_accession(acc)

    @staticmethod
    def _interface_score(result: Any) -> Optional[float]:
        """Pull an interface-confidence number out of a co-fold result.

        Field names vary by backend/version; try the common ones in priority
        order (ipTM is the standard interface metric).
        """
        if not isinstance(result, dict):
            return None
        for path in (("iptm",), ("ipTM",), ("interface_ptm",), ("confidence", "iptm"),
                     ("metrics", "iptm"), ("ranking_confidence",), ("ptm",), ("plddt",)):
            node: Any = result
            ok = True
            for k in path:
                if isinstance(node, dict) and k in node:
                    node = node[k]
                else:
                    ok = False
                    break
            if ok and isinstance(node, (int, float)):
                return float(node)
        return None

    def cofold(self, backend_tool: str, peptide: str, receptor: str, cyclic: bool = False) -> Dict[str, Any]:
        if backend_tool == "NvidiaNIM_boltz2":
            pep: Dict[str, Any] = {"id": "A", "molecule_type": "protein", "sequence": peptide}
            if cyclic:
                pep["cyclic"] = True  # boltz2 natively supports head-to-tail cyclic peptides
            args = {"polymers": [pep, {"id": "B", "molecule_type": "protein", "sequence": receptor}]}
        elif backend_tool == "NvidiaNIM_alphafold2_multimer":
            args = {"sequences": [peptide, receptor]}  # array of chains -> one complex
        else:  # openfold3: ONE input whose `molecules` array holds both chains (a co-fold)
            args = {"inputs": [{"input_id": "complex", "molecules": [
                {"type": "protein", "sequence": peptide},
                {"type": "protein", "sequence": receptor},
            ]}]}
        return self.run(backend_tool, args)


def main() -> int:
    ap = argparse.ArgumentParser(description="Phase 5 batch peptide:receptor co-folding screen.")
    ap.add_argument("--peptide", required=True, help="Peptide sequence.")
    ap.add_argument("--candidates", nargs="+", required=True, help="Candidate receptor gene symbols (keep <=8).")
    ap.add_argument("--backend", choices=list(_BACKENDS), default="boltz2")
    ap.add_argument("--assay-species", default=None, help="If set, also co-fold the lead candidate's ortholog in this species (e.g. mus_musculus) to test cross-species binding.")
    ap.add_argument("--cyclic", action="store_true", help="Treat the peptide as head-to-tail cyclic (boltz2 backend only).")
    ap.add_argument("--out", default=None, help="Optional JSON output path.")
    args = ap.parse_args()

    has_key = bool(os.environ.get("NVIDIA_API_KEY"))
    backend_tool = _BACKENDS[args.backend]
    cf = CoFolder(_load_tu())
    peptide = args.peptide.strip().upper()

    print("\n" + "=" * 72)
    print(f"CO-FOLD SCREEN  |  backend={args.backend} ({backend_tool})  |  key={'set' if has_key else 'MISSING -> DRY RUN'}")
    print("=" * 72)

    plan: List[Dict[str, Any]] = []
    for sym in args.candidates:
        seq = cf.receptor_sequence(sym)
        plan.append({"candidate": sym, "receptor_len": len(seq) if seq else None, "resolved": bool(seq), "_seq": seq})
        print(f"  {sym:<8} receptor sequence: {'resolved (%d aa)' % len(seq) if seq else 'NOT FOUND (skip)'}")

    if not has_key:
        print("-" * 72)
        print("DRY RUN: NVIDIA_API_KEY not set. Inputs above are verified; no co-fold run.")
        print("Set NVIDIA_API_KEY (free at build.nvidia.com; or `tooluniverse:setup-keys`) to score.")
        print(f"Would co-fold the peptide ({len(peptide)} aa) against {sum(1 for p in plan if p['resolved'])} resolved receptor(s).")
        if args.out:
            json.dump({"peptide": peptide, "plan": [{k: v for k, v in p.items() if k != '_seq'} for p in plan]}, open(args.out, "w"), indent=2)
        return 0

    print("-" * 72)
    results: List[Dict[str, Any]] = []
    for p in plan:
        if not p["resolved"]:
            continue
        sym = p["candidate"]
        print(f"  co-folding peptide : {sym} ...", flush=True)
        resp = cf.cofold(backend_tool, peptide, p["_seq"], cyclic=args.cyclic)
        score = cf._interface_score(cf._data(resp))
        results.append({"candidate": sym, "interface_score": score, "status": resp.get("status"),
                        "error": resp.get("error")})
        print(f"    -> interface score: {score if score is not None else 'unparsed (see raw)'}  [{resp.get('status')}]")

    results.sort(key=lambda r: (r["interface_score"] is None, -(r["interface_score"] or 0)))

    # optional cross-species check on the lead
    cross = None
    if args.assay_species and results and results[0]["interface_score"] is not None:
        lead = results[0]["candidate"]
        oseq = cf.ortholog_sequence(lead, args.assay_species)
        if oseq:
            print(f"  cross-species: co-folding peptide : {lead} ({args.assay_species}) ...", flush=True)
            r = cf.cofold(backend_tool, peptide, oseq, cyclic=args.cyclic)
            cross = {"candidate": lead, "species": args.assay_species, "interface_score": cf._interface_score(cf._data(r))}
            print(f"    -> {args.assay_species} interface score: {cross['interface_score']}")

    print("=" * 72)
    print("RANKED BY INTERFACE CONFIDENCE (higher = stronger predicted binding):")
    for i, r in enumerate(results, 1):
        print(f"  {i}. {r['candidate']:<8} {r['interface_score']}")
    if cross:
        print(f"\nCross-species: {cross['candidate']} human vs {cross['species']} interface — "
              f"a drop in the ortholog score mechanistically explains a species-specific negative.")

    if args.out:
        json.dump({"peptide": peptide, "backend": backend_tool, "results": results, "cross_species": cross},
                  open(args.out, "w"), indent=2)
        print(f"\nFull JSON -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
