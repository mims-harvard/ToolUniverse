#!/usr/bin/env python3
"""Keyless peptide target-deorphanization pipeline (Phases 1-4).

Given a peptide sequence (and, ideally, the hypothesized target gene that the
peptide does NOT actually bind, plus the phenotype it produces), enumerate and
rank the candidate real protein targets using only keyless ToolUniverse tools:

    characterization -> motif/signature (PROSITE + ELM regex) -> homology
    -> receptor-family panel (seeded, or SEEDLESS) -> phenotype anchor
    -> protease/degradation liability -> cross-species -> ranked shortlist

No API key is required. The optional structural confirmation step (co-folding)
lives in ``cofold_screen.py`` and needs NVIDIA_API_KEY.

Single peptide (the exendin-4 -> GLP1R control):

    python3 deorphanize_peptide.py \
        --sequence HGEGTFTSDLSKQMEEEAVRLFIEWLKNGGPSSGAPPPS \
        --hypothesized-target GLP1R \
        --phenotype "type 2 diabetes mellitus" --assay-species mus_musculus

Seedless (no hypothesized target -> derive candidate receptors from the motif):

    python3 deorphanize_peptide.py --sequence <SEQ> --phenotype "type 2 diabetes mellitus"

Batch (one record per FASTA entry; shared --phenotype/--assay-species):

    python3 deorphanize_peptide.py --fasta peptides.fasta --phenotype "type 2 diabetes mellitus"
"""

import argparse
import json
import re
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


def _as_list(node: Any, *keys: str) -> List[Any]:
    """Return a list from ``node`` (already a list, or under one of ``keys``)."""
    if isinstance(node, list):
        return node
    if isinstance(node, dict):
        for k in keys:
            if isinstance(node.get(k), list):
                return node[k]
    return []


# UniProt accepts organism common names; map the usual assay/source species.
_ORGANISM_COMMON = {
    "homo_sapiens": "human",
    "mus_musculus": "mouse",
    "rattus_norvegicus": "rat",
    "danio_rerio": "zebrafish",
    "drosophila_melanogaster": "fruit fly",
    "caenorhabditis_elegans": "Caenorhabditis elegans",
    "saccharomyces_cerevisiae": "yeast",
}

_CANONICAL_AA = set("ACDEFGHIKLMNPQRSTVWY")


def _organism_query(species: str) -> str:
    """Species token -> a UniProt organism filter (common name when known)."""
    return _ORGANISM_COMMON.get(species.lower(), species.replace("_", " "))


def _noncanonical(seq: str) -> Dict[str, Any]:
    """Flag residues outside the 20 standard AAs (BLAST/PROSITE assume canonical)."""
    extra = sorted({c for c in seq.upper() if c not in _CANONICAL_AA})
    return {
        "noncanonical_residues": extra,
        "is_canonical_linear": not extra,
        "note": (
            "non-standard residues present -> BLAST/PROSITE/ProtParam assume canonical "
            "linear L-amino acids and may mischaracterize this peptide. If it is a "
            "non-ribosomal/cyclic peptide, look it up by name with Norine_get_peptide "
            "and pass --cyclic to cofold_screen.py."
            if extra
            else "all residues are standard L-amino acids."
        ),
    }


def _pairwise_identity(aligned: Dict[str, str], a: str, b: str) -> Optional[Dict[str, Any]]:
    """Percent identity of two aligned sequences over non-gap shared columns."""
    sa, sb = aligned.get(a), aligned.get(b)
    if not sa or not sb or len(sa) != len(sb):
        return None
    cols = [(x, y) for x, y in zip(sa, sb) if x != "-" and y != "-"]
    if not cols:
        return None
    same = sum(1 for x, y in cols if x.upper() == y.upper())
    return {
        "percent_identity": round(100.0 * same / len(cols), 1),
        "n_substitutions": len(cols) - same,
        "aligned_columns": len(cols),
    }


def _parse_fasta_str(fasta: str) -> Dict[str, str]:
    """Parse an aligned/plain FASTA string into {name: sequence}."""
    out: Dict[str, str] = {}
    name: Optional[str] = None
    buf: List[str] = []
    for line in (fasta or "").splitlines():
        if line.startswith(">"):
            if name:
                out[name] = "".join(buf)
            name = line[1:].split()[0] if line[1:].split() else line[1:]
            buf = []
        elif line.strip():
            buf.append(line.strip())
    if name:
        out[name] = "".join(buf)
    return out


# Target-class router: a peptide's real target need not be a GPCR. Classifying the
# likely target class lets candidate generation ADAPT its enumeration strategy
# (and pick the right seedless search nouns) instead of assuming "receptor". Each
# entry: (class, keyword triggers in PROSITE/BLAST text, seedless search nouns).
_TARGET_CLASS_RULES = [
    ("gpcr_ligand",
     ("glucagon", "secretin", "incretin", "gip", "vip ", "pacap", "tachykinin",
      "bombesin", "melanocortin", "somatostatin", "angiotensin", "bradykinin",
      "orexin", "gnrh", "opioid", "neuropeptide", "calcitonin", "parathyroid"),
     ("receptor",)),
    ("guanylyl_cyclase_ligand",
     ("natriuretic", "guanylin", "uroguanylin"),
     ("receptor", "guanylate cyclase")),
    ("cytokine_or_growth_factor",
     ("interleukin", "interferon", "chemokine", "tumor necrosis", "growth factor",
      "erythropoietin", "leptin", "cytokine"),
     ("receptor",)),
    ("rtk_ligand",
     ("insulin", "epidermal growth factor", "fibroblast growth factor", "ephrin"),
     ("receptor",)),
    ("ion_channel_toxin",
     ("conotoxin", "scorpion toxin", "spider toxin", "sea anemone", "channel blocker",
      "potassium channel", "sodium channel", "calcium channel"),
     ("channel", "receptor")),
    ("protease_inhibitor_or_substrate",
     ("protease inhibitor", "serine protease inhibitor", "kunitz", "bowman-birk",
      "peptidase inhibitor", "serpin"),
     ("protease", "peptidase")),
    ("integrin_ligand",
     ("integrin", "disintegrin", "fibronectin"),
     ("integrin",)),
    ("antimicrobial",
     ("antimicrobial", "defensin", "cathelicidin", "bacteriocin"),
     ()),  # AMPs often act on the membrane, not a single protein target
]
_UNKNOWN_CLASS_NOUNS = ("receptor", "enzyme", "channel", "transporter")
# An HGNC gene group larger than this is a domain SUPERGROUP (e.g. "EF-hand domain
# containing" ~190 genes), not a ligand-target family — enumerating it floods the
# panel. Real target families (channels, secretin GPCRs, NPRs, protease subfamilies)
# are well under this; bound them like the InterPro route.
_HGNC_GROUP_CAP = 80
# A seed protein can sit in several InterPro FAMILY entries; enumerate only the
# first few to bound the number of InterPro_get_proteins_by_domain calls.
_INTERPRO_MAX_FAMILIES = 2


def _classify_target_class(
    signatures: List[Dict[str, str]],
    homology_defs: List[str],
    seq: str,
    amp_matched: bool = False,
) -> Dict[str, Any]:
    """Heuristically classify the peptide's likely target class from its motif/
    homology text + sequence features, so candidate generation can branch.

    Transparent and evidence-bearing: returns the matched class, the text that
    triggered it, and the seedless search nouns to use. Never authoritative — it
    only *steers* enumeration; phenotype + homology still drive the candidates.
    """
    hay = " ".join(
        [(s.get("description") or "") + " " + (s.get("name") or "") for s in signatures]
        + list(homology_defs or [])
    ).lower()

    def _result(cls, nouns, evidence):
        return {"target_class": cls, "seedless_nouns": list(nouns), "evidence": evidence}

    # Most specific signals first: an explicit RGD motif -> integrins.
    if "RGD" in seq.upper():
        return _result("integrin_ligand", ("integrin",), ["RGD motif in sequence"])
    # Keyword-driven classes from the motif/homology text.
    for cls, triggers, nouns in _TARGET_CLASS_RULES:
        hit = next((t for t in triggers if t in hay), None)
        if hit:
            return _result(cls, nouns, [f"text match: '{hit.strip()}'"])
    # Sequence-feature fallback: a short, cysteine-rich peptide with no named
    # family is most often a disulfide-stabilised toxin/knottin (ion channels,
    # proteases) rather than a linear hormone.
    cys = seq.upper().count("C")
    if seq and cys >= 4 and cys / len(seq) >= 0.15 and len(seq) <= 60:
        return _result("ion_channel_toxin", ("channel", "receptor", "protease"),
                       [f"cysteine-rich ({cys} Cys / {len(seq)} aa) -> disulfide-stabilised toxin"])
    if amp_matched:
        return _result("antimicrobial", (), ["AMPSphere exact match"])
    return _result("unknown", _UNKNOWN_CLASS_NOUNS, ["no class-specific signal; using broad search"])


class Pipeline:
    def __init__(self, tu, verbose: bool = True):
        self.tu = tu
        self.verbose = verbose

    def run(self, name: str, args: Dict[str, Any], attempts: int = 2) -> Dict[str, Any]:
        last = {"status": "error", "error": "no attempt"}
        for _ in range(max(1, attempts)):
            try:
                out = self.tu.run({"name": name, "arguments": args})
            except Exception as exc:  # never let one tool kill the pipeline
                last = {"status": "error", "error": f"{type(exc).__name__}: {exc}"}
                continue
            resp = out if isinstance(out, dict) else {"status": "success", "data": out}
            if resp.get("status") == "success":
                return resp
            # retry only transient upstream connection drops; surface other errors
            err = str(resp.get("error", "")).lower()
            if "aborted" not in err and "disconnect" not in err:
                return resp
            last = resp
        return last

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

    # ---- Phase 2a: motif / PROSITE signature ---------------------------
    def motif_families(self, seq: str) -> List[Dict[str, str]]:
        out: List[Dict[str, str]] = []
        scan = self._data(self.run("ScanProsite_scan_protein", {"seq": seq}))
        for m in scan.get("matchset", []) if isinstance(scan, dict) else []:
            ac = m.get("signature_ac")
            if not ac:
                continue
            entry = self._data(self.run("PROSITE_get_entry", {"accession": ac}))
            entry = entry if isinstance(entry, dict) else {}
            out.append({"accession": ac, "description": entry.get("description", ""), "name": entry.get("entry_name", "")})
        return out

    # ---- Phase 2a': ELM short-linear-motif regex match (enrichment) -----
    def elm_motif_match(self, seq: str, top: int = 6) -> List[Dict[str, Any]]:
        """Match the peptide against ELM ligand (LIG) motif regexes.

        LIG regexes are short and low-specificity, so results are ranked by
        rarity (ELM ``probability``, smaller = rarer) and each match is annotated
        with the Pfam domain it engages. Treat as low-confidence context, useful
        mainly for peptides whose PROSITE signature is not a named family.
        """
        lig = self._data(self.run("ELM_list_classes", {"operation": "list_classes", "motif_type": "LIG", "max_results": 300}))
        hits: List[Dict[str, Any]] = []
        for c in _as_list(lig, "classes", "elm_classes"):
            rgx = c.get("regex")
            try:
                if rgx and re.search(rgx, seq):
                    hits.append({"elm": c.get("elm_identifier"), "probability": c.get("probability"), "site": c.get("functional_site_name")})
            except re.error:
                continue
        hits.sort(key=lambda h: h["probability"] if h["probability"] is not None else 1.0)
        hits = hits[:top]
        for h in hits:
            dom = self._data(self.run("ELM_get_interaction_domains", {"operation": "get_interaction_domains", "elm_identifier": h["elm"]}))
            h["binding_domains"] = [
                {"pfam": m.get("pfam_accession"), "name": m.get("interaction_domain_name")}
                for m in _as_list(dom, "mappings", "interaction_domains", "data")[:3]
            ]
        return hits

    # ---- Phase 2b: homology (slow; optional) ---------------------------
    def homology_hits(self, seq: str, hitlist: int = 10) -> List[str]:
        data = self._data(self.run("BLAST_protein_search", {"sequence": seq, "database": "swissprot", "expect": 10.0, "hitlist_size": hitlist}))
        defs: List[str] = []
        if isinstance(data, dict):
            for aln in data.get("alignments") or data.get("hits") or []:
                d = aln.get("hit_def") or aln.get("description") or aln.get("definition")
                if d:
                    defs.append(d)
        return defs

    # ---- Phase 2c: target-family panel ---------------------------------
    def _accessions_to_symbols(self, accessions: List[str]) -> List[str]:
        """Batch-map UniProt accessions -> gene symbols in ONE UniProt query.

        InterPro returns members as UniProt accessions (no gene field), so resolve
        them in a single 'accession:A OR accession:B ...' search rather than N calls.
        """
        accessions = accessions[:60]
        if not accessions:
            return []
        q = " OR ".join(f"accession:{a}" for a in accessions)
        res = self._data(self.run("UniProt_search", {"query": q, "limit": 60}))
        syms: set = set()
        for r in _as_list(res, "results"):
            for g in r.get("gene_names") or []:
                if g:
                    syms.add(str(g).upper())
        return sorted(syms)

    def interpro_family_members(self, accession: Optional[str], cap: int = 60) -> List[str]:
        """Enumerate a target's protein family via InterPro — a GENERAL route that
        works for any target class (kinases, channels, proteases, GPCRs alike),
        unlike GPCRdb. From the seed's UniProt accession, take its InterPro FAMILY
        entries, list each family's HUMAN members (InterPro mixes organisms, so
        filter tax_id 9606), and map those accessions to gene symbols. Bounded so a
        broad superfamily does not explode the panel."""
        if not accession:
            return []
        entries = self._data(self.run("InterPro_get_entries_for_protein", {"accession": accession}))
        ipr_ids: List[str] = []
        for e in _as_list(entries, "entries", "results", "data"):
            if not isinstance(e, dict):
                continue
            etype = str(e.get("type") or e.get("entry_type") or "").lower()
            ipr = e.get("accession") or e.get("interpro_accession") or e.get("id")
            if ipr and str(ipr).upper().startswith("IPR") and etype == "family":
                ipr_ids.append(str(ipr))

        human_accs: set = set()
        for ipr in ipr_ids[:_INTERPRO_MAX_FAMILIES]:
            prots = self._data(self.run("InterPro_get_proteins_by_domain",
                                        {"domain_id": ipr, "page_size": 50, "reviewed_only": True}))
            fam = [
                p.get("accession")
                for p in _as_list(prots, "proteins", "results", "data")
                if isinstance(p, dict) and str(p.get("tax_id")) == "9606" and p.get("accession")
            ]
            if 1 < len(fam) <= cap:  # skip a singleton or a too-broad superfamily
                human_accs.update(fam)
        if not human_accs or len(human_accs) > cap:
            return []
        return self._accessions_to_symbols(sorted(human_accs))

    def family_panel(self, seed_symbol: str) -> Dict[str, Any]:
        """Enumerate the seed gene's family (seed + paralogs). HGNC gene-family is
        the general backbone (any target class); GPCRdb cross-checks GPCRs; InterPro
        cross-checks (or, for a target with no HGNC group, provides) the family."""
        panel: Dict[str, Dict[str, Any]] = {}
        meta: Dict[str, Any] = {"seed": seed_symbol}

        gene = self._data(self.run("HGNC_fetch_gene_by_symbol", {"symbol": seed_symbol}))
        gene = gene if isinstance(gene, dict) else {}
        meta["hgnc_id"] = gene.get("hgnc_id")
        uniprot = (gene.get("uniprot_ids") or [None])[0]
        meta["uniprot"] = uniprot
        meta["gene_group"] = gene.get("gene_group")
        for gid in gene.get("gene_group_id") or []:
            members = self._data(self.run("HGNC_fetch_gene_family_members", {"gene_group_id": str(gid)})) or []
            if len(members) > _HGNC_GROUP_CAP:
                # a domain supergroup (e.g. EF-hand), not a target family — skip it
                meta.setdefault("skipped_broad_groups", []).append({"gene_group_id": str(gid), "size": len(members)})
                continue
            for mem in members:
                if mem.get("symbol"):
                    panel.setdefault(mem["symbol"], {"sources": set()})["sources"].add("HGNC")

        # HGNC family group is authoritative when present; GPCRdb then only
        # ANNOTATES those symbols (its entry-names carry aliases like 'glr' for
        # GCGR, so do not let GPCRdb introduce non-HGNC symbols once HGNC succeeded).
        hgnc_authoritative = bool(panel)
        gp = self._data(self.run("GPCRdb_get_protein", {"protein": seed_symbol}))
        slug = gp.get("family") if isinstance(gp, dict) else None
        if slug:
            meta["gpcrdb_slug"] = slug
            subfam = "_".join(slug.split("_")[:3])  # trim to subfamily level
            listed = self._data(self.run("GPCRdb_list_proteins", {"family": subfam})) or {}
            for p in listed.get("proteins", []):
                en = p.get("entry_name") or ""
                if not en.endswith("_human"):
                    continue
                sym = en[: -len("_human")].upper()
                if hgnc_authoritative and sym not in panel:
                    continue  # skip GPCRdb alias not in the authoritative HGNC panel
                panel.setdefault(sym, {"sources": set()})["sources"].add("GPCRdb")

        # InterPro general cross-check / fallback. When HGNC grouped the family it
        # only annotates those members; when there is NO HGNC group (a target not
        # in a curated family) it supplies the panel — the route that generalizes
        # beyond GPCRs/curated groups.
        seed_up = seed_symbol.upper()
        for sym in self.interpro_family_members(uniprot):
            if hgnc_authoritative and sym not in panel and sym != seed_up:
                continue
            panel.setdefault(sym, {"sources": set()})["sources"].add("InterPro")

        for v in panel.values():
            v["sources"] = sorted(v["sources"])
        return {"panel": panel, "meta": meta}

    # ---- Phase 2c (seedless): derive seed targets from motif + homology -----
    @staticmethod
    def _family_keywords(signatures: List[Dict[str, str]], homology_defs: Optional[List[str]] = None) -> List[str]:
        """Family keywords from PROSITE descriptions AND BLAST hit names — so a
        peptide with NO named PROSITE family can still seed from its homologs."""
        stop = {"family", "signature", "domain", "receptor", "protein", "type", "like",
                "precursor", "isoform", "fragment", "chain", "human", "putative"}
        texts = [s.get("description") or "" for s in signatures] + list(homology_defs or [])
        out: List[str] = []
        for text in texts:
            for tok in re.split(r"[\s/,.;()\-]+", text.lower()):
                if len(tok) >= 4 and tok.isalpha() and tok not in stop and tok not in out:
                    out.append(tok)
        return out[:8]

    def seedless_seeds(
        self,
        signatures: List[Dict[str, str]],
        nouns: Optional[List[str]] = None,
        homology_defs: Optional[List[str]] = None,
        max_seeds: int = 4,
    ) -> Dict[str, Any]:
        """Derive candidate seed gene symbols when no hypothesized target is given.

        For each family keyword × target-class noun (e.g. 'receptor', 'channel',
        'protease'), UniProt_search("<kw> <noun>", human) and keep the gene symbols
        whose protein_name actually contains one of the nouns (dropping ligand /
        precursor hits). The nouns come from the target-class router, so this is no
        longer receptor-only — an ion-channel toxin seeds channels, a protease-
        targeting peptide seeds proteases, etc. These seeds feed family_panel().
        """
        nouns = [n.lower() for n in (nouns or ["receptor"])]
        kws = self._family_keywords(signatures, homology_defs)
        seeds: Dict[str, str] = {}
        for kw in kws:
            for noun in nouns:
                # organism takes a COMMON NAME ('human'), not a taxid; '9606' errors.
                res = self._data(self.run("UniProt_search", {"query": f"{kw} {noun}", "organism": "human", "limit": 5}))
                for r in _as_list(res, "results"):
                    pname = (r.get("protein_name") or "").lower()
                    if not any(n in pname for n in nouns):
                        continue  # keep target-class members, drop ligand/precursor hits
                    for g in r.get("gene_names") or []:
                        seeds.setdefault(g, f"{kw} {noun}")
                        if len(seeds) >= max_seeds:
                            break
                if len(seeds) >= max_seeds:
                    break
            if len(seeds) >= max_seeds:
                break
        return {"keywords": kws, "nouns": nouns, "seeds": seeds}

    # ---- Phase 2e: protease / degradation liability --------------------
    _DPP4_P2 = {"A", "P"}

    def protease_liability(self, seq: str) -> Dict[str, Any]:
        """Flag degradation liabilities (a peptide may be inactive in an assay
        because it is *cleaved*, not because it fails to bind)."""
        p2 = seq[1] if len(seq) > 1 else ""
        labile = p2 in self._DPP4_P2
        out: Dict[str, Any] = {
            "dpp4": {
                "p2_residue": p2,
                "labile": labile,
                "note": (f"position-2 {p2} -> DPP4-labile (rapid N-terminal truncation, like native GLP-1)"
                         if labile else f"position-2 {p2} -> DPP4-resistant (like exendin-4)"),
            }
        }
        clv = self._data(self.run("ELM_list_classes", {"operation": "list_classes", "motif_type": "CLV", "max_results": 100}))
        sites: List[Dict[str, Any]] = []
        for c in _as_list(clv, "classes", "elm_classes"):
            rgx = c.get("regex")
            try:
                m = re.search(rgx, seq) if rgx else None
            except re.error:
                m = None
            if m:
                sites.append({"elm": c.get("elm_identifier"), "site": c.get("functional_site_name"), "span": [m.start() + 1, m.end()]})
        out["cleavage_motifs"] = sites
        return out

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
            sym = (r.get("target") or {}).get("approvedSymbol")
            if sym:
                scores[sym] = r.get("score")
        scores["__efo__"] = efo  # carry the resolved id for the report
        return scores

    def phenotype_union(self, names: List[str]) -> Dict[str, Any]:
        """Union the OpenTargets anchor across SEVERAL phenotypes, keeping the max
        score per target. For an unknown peptide you rarely know the single right
        disease, so anchoring on every plausible phenotype (and taking the union)
        is more robust than betting on one."""
        scores: Dict[str, float] = {}
        efos: List[str] = []
        for name in names or []:
            pt = self.phenotype_targets(name)
            efo = pt.pop("__efo__", None)
            if efo:
                efos.append(f"{name} -> {efo}")
            for sym, sc in pt.items():
                if sc is None:
                    continue
                if sym not in scores or (scores[sym] or 0) < sc:
                    scores[sym] = sc
        return {"scores": scores, "efo": "; ".join(efos)}

    # ---- Phase 3: cross-species ----------------------------------------
    def ortholog_status(self, hgnc_id: Optional[str], assay_species: str) -> Dict[str, Any]:
        if not hgnc_id:
            return {}
        resp = self._data(self.run("Alliance_get_gene_orthologs", {"gene_id": hgnc_id, "stringency": "all", "limit": 60}))
        rows = _as_list(resp, "orthologs", "data")
        target = assay_species.replace("_", " ").lower().split()[-1]
        for o in rows:
            sp = str(o.get("species") or o.get("target_species") or o.get("organism") or "").lower()
            if target in sp:  # e.g. 'musculus' in 'Mus musculus'
                m = o.get("methods")
                count = len(m) if isinstance(m, list) else (m or o.get("method_count"))
                return {"present": True, "best_method_count": count}
        return {"present": bool(rows), "note": f"ortholog list returned but no {assay_species} match parsed"}

    # ---- Phase 3': ortholog sequences + binding-interface divergence -----
    def _human_sequence(self, symbol: str) -> Dict[str, Optional[str]]:
        gene = self._data(self.run("HGNC_fetch_gene_by_symbol", {"symbol": symbol}))
        acc = (gene.get("uniprot_ids") or [None])[0] if isinstance(gene, dict) else None
        return {"accession": acc, "sequence": self._sequence_for(acc)}

    def _species_sequence(self, symbol: str, species: str) -> Dict[str, Optional[str]]:
        """Resolve the ortholog's protein sequence in ``species`` via UniProt search."""
        res = self._data(self.run("UniProt_search", {"query": f"gene:{symbol}", "organism": _organism_query(species), "limit": 1}))
        rows = _as_list(res, "results")
        acc = rows[0].get("accession") if rows else None
        return {"accession": acc, "sequence": self._sequence_for(acc)}

    def _sequence_for(self, accession: Optional[str]) -> Optional[str]:
        if not accession:
            return None
        seq = self._data(self.run("UniProt_get_sequence_by_accession", {"accession": accession}))
        if isinstance(seq, str):
            return seq.strip() or None
        if isinstance(seq, dict):
            return seq.get("sequence") or seq.get("value")
        return None

    def cross_species_alignment(self, symbol: str, assay_species: str, source_species: Optional[str]) -> Dict[str, Any]:
        """Align the human ortholog vs the assay (and optional source) species and
        report sequence divergence — the mechanistic core of "binds in A, not B".

        Keyless full-length identity is a proxy for interface divergence (we cannot
        pinpoint the binding pocket without a structure); a low human-vs-assay
        identity flags the ortholog whose interface most plausibly diverged.
        """
        chains: Dict[str, str] = {}
        accs: Dict[str, Optional[str]] = {}
        human = self._human_sequence(symbol)
        if human["sequence"]:
            chains["human"] = human["sequence"]
            accs["human"] = human["accession"]
        species = {"assay": assay_species}
        if source_species:
            species["source"] = source_species
        for role, sp in species.items():
            got = self._species_sequence(symbol, sp)
            if got["sequence"]:
                chains[role] = got["sequence"]
                accs[role] = got["accession"]
        if len(chains) < 2:
            return {"status": "insufficient", "resolved": list(chains), "accessions": accs,
                    "note": "need >=2 ortholog sequences to align; some species not in UniProt "
                            "(source organism may be a protist absent from vertebrate-centric DBs). "
                            "Provide the source binding-partner sequence directly to align by hand."}
        fasta = "".join(f">{role}\n{seq}\n" for role, seq in chains.items())
        aln = self._data(self.run("EBI_msa_align", {"sequences": fasta, "method": "clustalo", "sequence_type": "protein"}))
        aln = aln if isinstance(aln, dict) else {}
        aligned_fasta = aln.get("aligned_fasta") or aln.get("alignment") or aln.get("fasta")
        aligned = _parse_fasta_str(aligned_fasta) if aligned_fasta else {}
        pairs: List[Dict[str, Any]] = []
        for other in ("assay", "source"):
            if "human" in aligned and other in aligned:
                pid = _pairwise_identity(aligned, "human", other)
                if pid:
                    pairs.append({"pair": f"human_vs_{other}", "species": species.get(other), **pid})
        return {"status": "ok" if pairs else "aligned_unparsed", "accessions": accs, "pairs": pairs,
                "note": "lower human-vs-assay identity = the ortholog whose binding interface most "
                        "plausibly diverged, a mechanistic explanation for a species-specific negative."}

    def representative_pdb(self, symbol: str, accession: Optional[str]) -> Optional[Dict[str, Any]]:
        """Best PDB structure for the candidate (keyless) — feeds ClusPro docking."""
        if not accession:
            gene = self._data(self.run("HGNC_fetch_gene_by_symbol", {"symbol": symbol}))
            accession = (gene.get("uniprot_ids") or [None])[0] if isinstance(gene, dict) else None
        if not accession:
            return None
        best = self._data(self.run("PDBeSIFTS_get_best_structures", {"uniprot_accession": accession}))
        rows = _as_list(best, "structures", "best_structures", "data")
        if isinstance(best, dict) and not rows and isinstance(best.get(accession), list):
            rows = best[accession]  # SIFTS keys results under the accession
        if not rows:
            return None
        top = rows[0]
        return {"pdb_id": top.get("pdb_id") or top.get("pdbId"), "uniprot": accession,
                "chain": top.get("chain_id") or top.get("chainId")}


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


def _rank_key(r: Dict[str, Any]):
    rank = {"Tier 1 (family + phenotype)": 0, "Tier 2 (family only)": 1, "Tier 3 (phenotype only)": 2}.get(r["tier"], 3)
    if r["is_hypothesized_target"]:
        rank = 4
    # Within a tier, break ties by phenotype score, then by how many independent
    # family resources agree (HGNC + InterPro + GPCRdb). A 2-source-corroborated
    # member is more likely the true tight family than an HGNC-only loose-group
    # member — this floats the cross-checked core above noisy broad-group panels.
    return (rank, -(r["phenotype_score"] or 0), -len(r.get("family_sources") or []))


def _build_panel(pipe: Pipeline, args, result: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Seed family (if a hypothesized target is given) UNION the sequence-derived
    candidates (motif + homology, class-aware nouns). Running the sequence-derived
    derivation in BOTH modes is deliberate: the hypothesized seed may be WRONG (the
    premise of deorphanization), so the real target can sit in a DIFFERENT family;
    the sequence-derived panel keeps that family in play instead of being blinded by
    the seed. Degrades gracefully when the UniProt resolver is down (seeds empty ->
    seed family / phenotype carry the panel)."""
    panel: Dict[str, Dict[str, Any]] = {}
    if args.hypothesized_target:
        fp = pipe.family_panel(args.hypothesized_target)
        panel = fp["panel"]
        result["family_meta"] = fp["meta"]
    pipe.log(f"[{result.get('label')}] sequence-derived candidates ({result['target_class']['target_class']})")
    sl = pipe.seedless_seeds(
        result["signatures"],
        nouns=result["target_class"]["seedless_nouns"],
        homology_defs=result.get("homology_hits") or [],
    )
    result["seedless"] = sl
    for seed in sl["seeds"]:
        for sym, info in pipe.family_panel(seed)["panel"].items():
            existing = panel.get(sym, {}).get("sources", [])
            panel[sym] = {"sources": sorted(set(existing) | set(info["sources"]))}
    return panel


def analyze_one(pipe: Pipeline, label: str, seq: str, args, pheno: Dict[str, float], efo: Optional[str]) -> Dict[str, Any]:
    result: Dict[str, Any] = {"label": label, "sequence": seq, "hypothesized_target": args.hypothesized_target}

    pipe.log(f"[{label}] characterization + motif")
    result["properties"] = pipe.characterize(seq)
    result["peptide_form"] = _noncanonical(seq)
    result["signatures"] = pipe.motif_families(seq)
    result["elm_motifs"] = pipe.elm_motif_match(seq)
    result["protease_liability"] = pipe.protease_liability(seq)
    if not args.no_blast:
        pipe.log(f"[{label}] BLAST homology (slow)")
        result["homology_hits"] = pipe.homology_hits(seq)

    # Target-class router: classify the likely target class so candidate
    # generation adapts (a peptide's real target need not be a GPCR).
    result["target_class"] = _classify_target_class(
        result["signatures"], result.get("homology_hits") or [], seq
    )

    panel = _build_panel(pipe, args, result)

    candidates = set(panel) | (set(pheno) & set(panel))
    if not candidates and pheno:
        candidates = set(list(pheno)[:15])  # phenotype-only fallback

    rows: List[Dict[str, Any]] = []
    for sym in sorted(candidates):
        in_panel = sym in panel
        pscore = pheno.get(sym)
        is_hypoth = bool(args.hypothesized_target and sym.upper() == args.hypothesized_target.upper())
        rows.append({
            "gene": sym, "tier": tier(in_panel, pscore, is_hypoth), "in_family_panel": in_panel,
            "family_sources": panel.get(sym, {}).get("sources", []), "phenotype_score": pscore,
            "is_hypothesized_target": is_hypoth,
        })
    rows.sort(key=_rank_key)
    leads_done = 0
    for r in rows[:5]:
        if r["is_hypothesized_target"]:
            continue
        g = pipe._data(pipe.run("HGNC_fetch_gene_by_symbol", {"symbol": r["gene"]}))
        acc = (g.get("uniprot_ids") or [None])[0] if isinstance(g, dict) else None
        r["cross_species"] = pipe.ortholog_status(g.get("hgnc_id") if isinstance(g, dict) else None, args.assay_species)
        # For the top few real-target hypotheses, do the work the skill promised:
        # resolve ortholog sequences and align the binding interface across species,
        # and suggest a ClusPro-ready PDB structure.
        if leads_done < 3:
            pipe.log(f"[{label}] cross-species interface alignment: {r['gene']}")
            r["interface_alignment"] = pipe.cross_species_alignment(r["gene"], args.assay_species, args.source_species)
            r["representative_pdb"] = pipe.representative_pdb(r["gene"], acc)
            leads_done += 1
    result["ranked_candidates"] = rows
    result["phenotype_efo"] = efo

    _print_summary(args, result, panel, rows)
    return result


def _print_summary(args, result, panel, rows) -> None:
    seq = result["sequence"]
    print("\n" + "=" * 72)
    print(f"PEPTIDE DEORPHANIZATION  |  {result['label']}  |  {seq[:34]}{'...' if len(seq) > 34 else ''}")
    print("=" * 72)
    p = result["properties"]
    print(f"len={p.get('length')}  MW~{p.get('mw_average')}  pI~{p.get('pI_protparam')}  GRAVY={p.get('gravy')}")
    form = result.get("peptide_form", {})
    if form.get("noncanonical_residues"):
        print(f"NON-CANONICAL residues {form['noncanonical_residues']} -> sequence tools may "
              "mischaracterize; if NRP/cyclic use Norine_get_peptide + cofold --cyclic")
    tc = result.get("target_class")
    if tc:
        print(f"target class: {tc['target_class']}  ({'; '.join(tc.get('evidence', []))})"
              + (f"  -> seedless nouns: {tc['seedless_nouns']}" if tc.get("seedless_nouns") else ""))
    for s in result.get("signatures") or []:
        print(f"signature: {s['accession']}  {s['description']}")
    elm = result.get("elm_motifs") or []
    if elm:
        doms = ", ".join(d["name"] for h in elm[:3] for d in h.get("binding_domains", []) if d.get("name"))
        print(f"ELM LIG motifs (rarest): {', '.join(h['elm'] for h in elm[:3])}" + (f"  -> domains: {doms}" if doms else ""))
    pl = result.get("protease_liability", {})
    dpp4 = pl.get("dpp4", {})
    print(f"protease: DPP4 {dpp4.get('p2_residue')}@P2 -> {'LABILE' if dpp4.get('labile') else 'resistant'}; "
          f"cleavage motifs: {len(pl.get('cleavage_motifs', []))}")
    if args.hypothesized_target:
        print(f"seed family of {args.hypothesized_target}: {result.get('family_meta', {}).get('gene_group')}")
    sl = result.get("seedless") or {}
    if sl.get("seeds"):
        print(f"sequence-derived (keywords {sl['keywords']} x nouns {sl.get('nouns')}) -> seeds {dict(sl['seeds'])}")
    elif sl and not args.hypothesized_target:
        print(f"sequence-derived: keywords {sl.get('keywords')} x nouns {sl.get('nouns')} -> resolver returned nothing "
              "(UniProt transient, or target not named like one of the nouns). Showing phenotype-anchored "
              "candidates only; pass --hypothesized-target for clean family enumeration.")
    print(f"panel ({len(panel)}): {sorted(panel)[:20]}{' ...' if len(panel) > 20 else ''}")
    if args.phenotype:
        print(f"phenotype anchor(s): {', '.join(args.phenotype)} -> {result.get('phenotype_efo')}")
    print("-" * 72)
    print(f"{'GENE':<10}{'TIER':<32}{'PHENO':<8}{'FAMILY':<14}{'X-SPECIES'}")
    for r in rows:
        xs = r.get("cross_species", {})
        xs_s = ("present" if xs.get("present") else "") if xs else ""
        ps = f"{r['phenotype_score']:.3f}" if r["phenotype_score"] is not None else "-"
        print(f"{r['gene']:<10}{r['tier']:<32}{ps:<8}{','.join(r['family_sources']) or '-':<14}{xs_s}")
    # Lead-candidate cross-species interface divergence + ClusPro-ready PDB
    for r in rows:
        ia = r.get("interface_alignment")
        if ia and ia.get("pairs"):
            spans = "; ".join(f"{x['pair']} {x['percent_identity']}% id ({x['n_substitutions']} subs)" for x in ia["pairs"])
            print(f"  x-species {r['gene']}: {spans}")
        elif ia and ia.get("status") == "insufficient":
            print(f"  x-species {r['gene']}: {ia['note']}")
        pdb = r.get("representative_pdb")
        if pdb and pdb.get("pdb_id"):
            print(f"  ClusPro-ready PDB for {r['gene']}: {pdb['pdb_id']} (chain {pdb.get('chain') or '?'}, {pdb['uniprot']})")
    print("=" * 72)
    if dpp4.get("labile"):
        print("NOTE: peptide is DPP4-labile -> an assay-negative result may be DEGRADATION, not")
        print("non-binding. Re-test with a DPP4 inhibitor or a protease-resistant analog.")
    if args.hypothesized_target:
        print(f"NOTE: {args.hypothesized_target} was the hypothesized target (assay-negative). The Tier-1/2")
        print("alternatives above are the testable real-target hypotheses to validate next.")


def _parse_fasta(path: str) -> Dict[str, str]:
    seqs: Dict[str, str] = {}
    name: Optional[str] = None
    buf: List[str] = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line.startswith(">"):
                if name:
                    seqs[name] = "".join(buf)
                name = (line[1:].split() or [f"seq{len(seqs) + 1}"])[0]
                buf = []
            elif line:
                buf.append(line)
    if name:
        seqs[name] = "".join(buf)
    return seqs


def main() -> int:
    ap = argparse.ArgumentParser(description="Keyless peptide target deorphanization (Phases 1-4).")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--sequence", help="Single peptide amino-acid sequence (1-letter).")
    src.add_argument("--fasta", help="FASTA file of peptides for BATCH mode (one record each).")
    ap.add_argument("--hypothesized-target", default=None, help="Gene symbol the peptide was assumed to hit (seeds family enumeration). Omit for SEEDLESS mode.")
    ap.add_argument("--phenotype", action="append", default=None, metavar="DISEASE",
                    help="Disease name for the OpenTargets anchor, e.g. 'type 2 diabetes mellitus'. Repeatable: pass --phenotype several times to anchor on every plausible phenotype and union the target sets (best for an unknown peptide).")
    ap.add_argument("--assay-species", default="mus_musculus", help="Species of the negative binding assay (cross-species reconciliation).")
    ap.add_argument("--source-species", default=None, help="Species where binding WAS observed (e.g. the source organism). Adds a 3-way human/assay/source interface alignment. Protists are often absent from UniProt — supply the partner sequence by hand if unresolved.")
    ap.add_argument("--no-blast", action="store_true", help="Skip the slow BLAST homology route.")
    ap.add_argument("--out", default=None, help="Optional path to write the full JSON result.")
    args = ap.parse_args()

    pipe = Pipeline(_load_tu())
    peptides = _parse_fasta(args.fasta) if args.fasta else {"peptide": args.sequence.strip().upper()}

    pheno: Dict[str, float] = {}
    efo: Optional[str] = None
    if args.phenotype:
        pipe.log(f"phenotype anchor (OpenTargets) — {len(args.phenotype)} phenotype(s), shared across peptides")
        pu = pipe.phenotype_union(args.phenotype)
        pheno, efo = pu["scores"], pu["efo"]

    all_results = {label: analyze_one(pipe, label, seq.upper(), args, pheno, efo) for label, seq in peptides.items()}

    if args.out:
        with open(args.out, "w") as f:
            json.dump(all_results if args.fasta else next(iter(all_results.values())), f, indent=2, default=str)
        print(f"\nFull JSON -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
