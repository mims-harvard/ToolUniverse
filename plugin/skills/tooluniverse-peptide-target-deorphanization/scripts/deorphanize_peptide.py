#!/usr/bin/env python3
"""Keyless peptide target-deorphanization pipeline (Phases 1-4).

Given a peptide sequence (and, ideally, the hypothesized target gene that the
peptide does NOT actually bind, plus the phenotype it produces), enumerate and
rank the candidate real protein targets using only keyless ToolUniverse tools:

    characterization -> motif/signature -> homology -> receptor-family panel
    -> phenotype anchor -> cross-species -> ranked shortlist

No API key is required. The optional structural confirmation step (co-folding)
lives in ``cofold_screen.py`` and needs NVIDIA_API_KEY.

Example (the exendin-4 -> GLP1R control):

    python3 deorphanize_peptide.py \
        --sequence HGEGTFTSDLSKQMEEEAVRLFIEWLKNGGPSSGAPPPS \
        --hypothesized-target GLP1R \
        --phenotype "type 2 diabetes mellitus" \
        --assay-species mus_musculus
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional


def _load_tu():
    """Load ToolUniverse, tolerating both installed-package and in-repo runs."""
    try:
        from tooluniverse import ToolUniverse
    except ImportError:
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src"))
        from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()
    return tu


class Pipeline:
    def __init__(self, tu, verbose: bool = True):
        self.tu = tu
        self.verbose = verbose

    def run(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            out = self.tu.run({"name": name, "arguments": args})
        except Exception as exc:  # never let one tool kill the pipeline
            return {"status": "error", "error": f"{type(exc).__name__}: {exc}"}
        return out if isinstance(out, dict) else {"status": "success", "data": out}

    @staticmethod
    def _data(resp: Dict[str, Any]) -> Any:
        return resp.get("data") if isinstance(resp, dict) and resp.get("status") == "success" else None

    def log(self, msg: str) -> None:
        if self.verbose:
            print(f"  {msg}", file=sys.stderr)

    # ---- Phase 1: characterization -------------------------------------
    def characterize(self, seq: str) -> Dict[str, Any]:
        props: Dict[str, Any] = {}
        pc = self._data(self.run("PepCalc_peptide_properties", {"seq": seq}))
        if isinstance(pc, dict):
            props["length"] = pc.get("seqLength")
            props["mw_monoisotopic"] = pc.get("molecularWeight")
            props["mw_average"] = pc.get("molecularWeightAverage")
            props["pI_pepcalc"] = pc.get("isoelectricPoint")
            props["formula"] = pc.get("formula")
        pp = self._data(self.run("ProtParam_calculate", {"sequence": seq}))
        if isinstance(pp, dict):
            props["pI_protparam"] = pp.get("isoelectric_point")
            props["gravy"] = pp.get("gravy")
            props["instability_index"] = pp.get("instability_index")
            props["mw_protparam"] = pp.get("molecular_weight_da")
        return props

    # ---- Phase 2a: motif / signature -----------------------------------
    def motif_families(self, seq: str) -> List[Dict[str, str]]:
        out: List[Dict[str, str]] = []
        scan = self._data(self.run("ScanProsite_scan_protein", {"seq": seq}))
        matches = (scan or {}).get("matchset") if isinstance(scan, dict) else None
        for m in matches or []:
            ac = m.get("signature_ac")
            if not ac:
                continue
            entry = self._data(self.run("PROSITE_get_entry", {"accession": ac}))
            desc = (entry or {}).get("description") if isinstance(entry, dict) else None
            out.append({"accession": ac, "description": desc or "", "name": (entry or {}).get("entry_name", "")})
        return out

    # ---- Phase 2b: homology (slow; optional) ---------------------------
    def homology_hits(self, seq: str, hitlist: int = 10) -> List[str]:
        resp = self.run(
            "BLAST_protein_search",
            {"sequence": seq, "database": "swissprot", "expect": 10.0, "hitlist_size": hitlist},
        )
        data = self._data(resp)
        defs: List[str] = []
        if isinstance(data, dict):
            for aln in data.get("alignments") or data.get("hits") or []:
                d = aln.get("hit_def") or aln.get("description") or aln.get("definition")
                if d:
                    defs.append(d)
        return defs

    # ---- Phase 2c: receptor-family panel -------------------------------
    def family_panel(self, seed_symbol: str) -> Dict[str, Any]:
        """Enumerate the seed gene's family (seed + paralogs) via HGNC + GPCRdb."""
        panel: Dict[str, Dict[str, Any]] = {}
        meta: Dict[str, Any] = {"seed": seed_symbol}

        gene = self._data(self.run("HGNC_fetch_gene_by_symbol", {"symbol": seed_symbol}))
        group_ids = (gene or {}).get("gene_group_id") or []
        meta["hgnc_id"] = (gene or {}).get("hgnc_id")
        meta["uniprot"] = ((gene or {}).get("uniprot_ids") or [None])[0]
        meta["gene_group"] = (gene or {}).get("gene_group")
        for gid in group_ids:
            members = self._data(self.run("HGNC_fetch_gene_family_members", {"gene_group_id": str(gid)}))
            for mem in members or []:
                sym = mem.get("symbol")
                if sym:
                    panel.setdefault(sym, {"sources": set()})["sources"].add("HGNC")

        # HGNC family group is authoritative when present; GPCRdb then only
        # ANNOTATES those symbols (its entry-names carry aliases like 'glr' for
        # GCGR, so do not let GPCRdb introduce non-HGNC symbols once HGNC succeeded).
        hgnc_authoritative = bool(panel)
        gp = self._data(self.run("GPCRdb_get_protein", {"protein": seed_symbol}))
        slug = (gp or {}).get("family") if isinstance(gp, dict) else None
        if slug:
            meta["gpcrdb_slug"] = slug
            subfam = "_".join(slug.split("_")[:3])  # trim to subfamily level
            listed = self._data(self.run("GPCRdb_list_proteins", {"family": subfam})) or {}
            for p in listed.get("proteins", []):
                en = (p.get("entry_name") or "")
                if not en.endswith("_human"):
                    continue
                sym = en[: -len("_human")].upper()
                if hgnc_authoritative and sym not in panel:
                    continue  # skip GPCRdb alias not in the authoritative HGNC panel
                panel.setdefault(sym, {"sources": set()})["sources"].add("GPCRdb")

        for v in panel.values():
            v["sources"] = sorted(v["sources"])
        return {"panel": panel, "meta": meta}

    # ---- Phase 2d: phenotype anchor ------------------------------------
    def phenotype_targets(self, disease_name: str) -> Dict[str, float]:
        srch = self._data(self.run("OpenTargets_get_disease_id_description_by_name", {"diseaseName": disease_name}))
        # response shape: data['search']['hits'][0]['id']
        hits = ((srch or {}).get("search") or {}).get("hits") if isinstance(srch, dict) else None
        efo = hits[0].get("id") if hits else None
        if not efo:
            return {}
        tg = self._data(self.run("OpenTargets_get_associated_targets_by_disease_efoId", {"efoId": efo}))
        # response shape: data['disease']['associatedTargets']['rows'][*]{target.approvedSymbol, score}
        rows = ((((tg or {}).get("disease") or {}).get("associatedTargets") or {}).get("rows")) if isinstance(tg, dict) else None
        scores: Dict[str, float] = {}
        for r in rows or []:
            sym = ((r.get("target") or {}).get("approvedSymbol"))
            if sym:
                scores[sym] = r.get("score")
        scores["__efo__"] = efo  # carry the resolved id for the report
        return scores

    # ---- Phase 3: cross-species ----------------------------------------
    def ortholog_status(self, hgnc_id: Optional[str], assay_species: str) -> Dict[str, Any]:
        if not hgnc_id:
            return {}
        resp = self._data(self.run("Alliance_get_gene_orthologs", {"gene_id": hgnc_id, "stringency": "all", "limit": 60}))
        rows = resp if isinstance(resp, list) else (resp or {}).get("orthologs") or (resp or {}).get("data") or []
        target = assay_species.replace("_", " ").lower()
        for o in rows or []:
            sp = str(o.get("species") or o.get("target_species") or o.get("organism") or "").lower()
            if target.split()[-1] in sp:  # e.g. 'musculus' in 'Mus musculus'
                return {"present": True, "best_method_count": o.get("methods") or o.get("method_count"), "raw": {k: o.get(k) for k in list(o)[:6]}}
        return {"present": bool(rows), "note": f"ortholog list returned but no {assay_species} match parsed"}


def tier(in_panel: bool, pheno_score: Optional[float], is_hypoth: bool) -> str:
    if is_hypoth:
        return "HYPOTHESIZED (tested negative)"
    if in_panel and pheno_score is not None:
        return "Tier 1 (family + phenotype)"
    if in_panel:
        return "Tier 2 (family only)"
    if pheno_score is not None:
        return "Tier 3 (phenotype only)"
    return "Tier 3 (weak)"


def main() -> int:
    ap = argparse.ArgumentParser(description="Keyless peptide target deorphanization (Phases 1-4).")
    ap.add_argument("--sequence", required=True, help="Peptide amino-acid sequence (1-letter).")
    ap.add_argument("--hypothesized-target", default=None, help="Gene symbol the peptide was assumed to hit (seeds family enumeration), e.g. GLP1R.")
    ap.add_argument("--phenotype", default=None, help="Disease/phenotype name for the OpenTargets anchor, e.g. 'type 2 diabetes mellitus'.")
    ap.add_argument("--assay-species", default="mus_musculus", help="Species of the negative binding assay (for cross-species reconciliation).")
    ap.add_argument("--no-blast", action="store_true", help="Skip the slow BLAST homology route.")
    ap.add_argument("--out", default=None, help="Optional path to write the full JSON result.")
    args = ap.parse_args()

    pipe = Pipeline(_load_tu())
    seq = args.sequence.strip().upper()
    result: Dict[str, Any] = {"sequence": seq, "hypothesized_target": args.hypothesized_target}

    pipe.log("Phase 1: characterization")
    result["properties"] = pipe.characterize(seq)
    pipe.log("Phase 2a: PROSITE/ELM signature")
    result["signatures"] = pipe.motif_families(seq)
    if not args.no_blast:
        pipe.log("Phase 2b: BLAST homology (slow, swissprot)")
        result["homology_hits"] = pipe.homology_hits(seq)

    panel: Dict[str, Dict[str, Any]] = {}
    if args.hypothesized_target:
        pipe.log("Phase 2c: receptor-family panel from hypothesized target")
        fp = pipe.family_panel(args.hypothesized_target)
        panel = fp["panel"]
        result["family_meta"] = fp["meta"]

    pheno: Dict[str, float] = {}
    if args.phenotype:
        pipe.log("Phase 2d: phenotype anchor (OpenTargets)")
        pheno = pipe.phenotype_targets(args.phenotype)
        result["phenotype_efo"] = pheno.pop("__efo__", None)

    # Build the candidate set = family panel UNION phenotype-supported family members
    candidates = set(panel) | (set(pheno) & set(panel))
    if not candidates and pheno:
        candidates = set(list(pheno)[:15])  # phenotype-only fallback

    pipe.log("Phase 3: cross-species + ranking")
    rows: List[Dict[str, Any]] = []
    for sym in sorted(candidates):
        in_panel = sym in panel
        pscore = pheno.get(sym)
        is_hypoth = bool(args.hypothesized_target and sym.upper() == args.hypothesized_target.upper())
        rows.append(
            {
                "gene": sym,
                "tier": tier(in_panel, pscore, is_hypoth),
                "in_family_panel": in_panel,
                "family_sources": panel.get(sym, {}).get("sources", []),
                "phenotype_score": pscore,
                "is_hypothesized_target": is_hypoth,
            }
        )

    # cross-species only for the leading non-hypothesized candidates (limit calls)
    def sort_key(r):
        rank = {"Tier 1 (family + phenotype)": 0, "Tier 2 (family only)": 1, "Tier 3 (phenotype only)": 2}.get(r["tier"], 3)
        if r["is_hypothesized_target"]:
            rank = 4
        return (rank, -(r["phenotype_score"] or 0))

    rows.sort(key=sort_key)
    for r in rows[:5]:
        if r["is_hypothesized_target"]:
            continue
        g = pipe._data(pipe.run("HGNC_fetch_gene_by_symbol", {"symbol": r["gene"]}))
        hid = (g or {}).get("hgnc_id") if isinstance(g, dict) else None
        r["cross_species"] = pipe.ortholog_status(hid, args.assay_species)

    result["ranked_candidates"] = rows

    # ---- human-readable summary ----
    print("\n" + "=" * 72)
    print(f"PEPTIDE DEORPHANIZATION  |  {seq[:40]}{'...' if len(seq) > 40 else ''}")
    print("=" * 72)
    p = result["properties"]
    print(f"len={p.get('length')}  MW~{p.get('mw_average')}  pI~{p.get('pI_protparam')}  GRAVY={p.get('gravy')}")
    if result.get("signatures"):
        for s in result["signatures"]:
            print(f"signature: {s['accession']}  {s['description']}")
    if args.hypothesized_target:
        fm = result.get("family_meta", {})
        print(f"family of {args.hypothesized_target}: {fm.get('gene_group')}  (panel: {sorted(panel)})")
    if args.phenotype:
        print(f"phenotype anchor: {args.phenotype} -> {result.get('phenotype_efo')}")
    print("-" * 72)
    print(f"{'GENE':<10}{'TIER':<32}{'PHENO':<8}{'FAMILY':<14}{'X-SPECIES'}")
    for r in rows:
        xs = r.get("cross_species", {})
        xs_s = ("present" if xs.get("present") else "") if xs else ""
        ps = f"{r['phenotype_score']:.3f}" if r["phenotype_score"] is not None else "-"
        print(f"{r['gene']:<10}{r['tier']:<32}{ps:<8}{','.join(r['family_sources']) or '-':<14}{xs_s}")
    print("=" * 72)
    if args.hypothesized_target:
        print(f"NOTE: {args.hypothesized_target} was the hypothesized target (assay-negative). The Tier-1/2")
        print("alternatives above are the testable real-target hypotheses to validate next.")

    if args.out:
        with open(args.out, "w") as f:
            json.dump(result, f, indent=2, default=str)
        print(f"\nFull JSON -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
