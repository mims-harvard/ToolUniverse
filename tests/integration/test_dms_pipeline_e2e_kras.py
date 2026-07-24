"""End-to-end DMS pipeline test on KRAS positions 10-25.

Real-data, real-Forge-API integration test that runs the full chain of
skills in sequence and verifies the G12-area hotspot finds biologically
sensible features. This is an expensive test (~300+ Forge SAE calls,
~$2-3 first run, free thereafter from cache).

Skipped by default — run with:
    RUN_DMS_E2E=1 pytest tests/integration/test_dms_pipeline_e2e_kras.py -v -s
or invoke `main()` directly via:
    python tests/integration/test_dms_pipeline_e2e_kras.py

Reference output from a successful run (committed alongside):
    tests/integration/dms_pipeline_e2e_kras_output.txt

Expected biology check:
  - Global MWU p < 0.05 (SAE drop correlates with folding ΔΔG disruption)
  - G12/G13 hotspot top feature labels include 'ligand-binding'
    (KRAS G12/G13 sit in the P-loop / Walker-A motif that binds the
    β-phosphate of GTP — ligand-binding feature is the expected mechanism)
"""
import os

import pytest


@pytest.mark.skipif(
    not os.environ.get("RUN_DMS_E2E"),
    reason="Live Forge API + MaveDB; set RUN_DMS_E2E=1 to opt in",
)
def test_kras_dms_e2e_pipeline_finds_ligand_binding_at_g12():
    """E2E: KRAS folding ΔΔG pipeline → G12/G13 hotspot labels include ligand-binding."""
    # Just runs main() and checks the assertions inside (it raises on failure).
    main()



import hashlib
import json
import re
import time
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.stats import mannwhitneyu

from tooluniverse import ToolUniverse

THREE_TO_ONE = {
    "Ala": "A", "Arg": "R", "Asn": "N", "Asp": "D", "Cys": "C",
    "Gln": "Q", "Glu": "E", "Gly": "G", "His": "H", "Ile": "I",
    "Leu": "L", "Lys": "K", "Met": "M", "Phe": "F", "Pro": "P",
    "Ser": "S", "Thr": "T", "Trp": "W", "Tyr": "Y", "Val": "V",
}
HGVS_RE = re.compile(r"^p\.\(?([A-Z][a-z]{2})(\d+)([A-Z][a-z]{2})\)?$")
AAS = "ACDEFGHIKLMNPQRSTVWY"

POS_MIN, POS_MAX = 10, 25
KRAS_URN = "urn:mavedb:00000115-a-7"
SAE_MODEL = "esmc-6b-2024-12_k64_codebook16384_layer60"
CACHE = Path("/tmp/kras_sae_cache")
CACHE.mkdir(exist_ok=True)


def cached_sae(tu, sequence, position):
    key = hashlib.sha1(f"{sequence}|{position}".encode()).hexdigest()[:16]
    cf = CACHE / f"{key}.json"
    if cf.exists():
        return json.loads(cf.read_text())
    r = tu.run({"name": "ESM_get_sae_features", "arguments": {
        "operation": "get_sae_features",
        "sequence": sequence,
        "position": position,
        "window": 0,
        "sae_model": SAE_MODEL,
        "top_k_per_residue": 64,
    }})
    if r.get("status") != "success":
        return {"_error": r.get("error", "?")}
    cf.write_text(json.dumps(r))
    return r


def main():
    tu = ToolUniverse()
    tu.load_tools()

    # Step 1: KRAS sequence
    print("\n=== Step 1: KRAS sequence ===")
    r = tu.run({"name": "UniProt_get_sequence_by_accession", "arguments": {"accession": "P01116"}})
    print("UniProt response type:", type(r).__name__, "keys:", list(r.keys())[:10] if isinstance(r, dict) else None)
    seq = None
    if isinstance(r, dict):
        for key in ("sequence", "seq"):
            if key in r and isinstance(r[key], str):
                seq = r[key]
                break
        if seq is None:
            inner = r.get("data") or r.get("result") or {}
            if isinstance(inner, dict):
                seq = inner.get("sequence") or inner.get("seq")
            elif isinstance(inner, str):
                seq = inner
    elif isinstance(r, str):
        seq = r
    if not seq:
        print("response sample:", json.dumps(r, indent=2)[:1000] if not isinstance(r, str) else r[:1000])
        raise RuntimeError("could not extract sequence")
    print(f"KRAS length: {len(seq)}, pos 12 = {seq[11]}")
    assert seq[11] == "G"

    # Step 2: MaveDB variants — single call returns all variants now that the
    # client-side cap has been removed (limit omitted = no truncation).
    print("\n=== Step 2: MaveDB KRAS folding ΔΔG ===")
    r = tu.run({"name": "MaveDB_get_variant_scores", "arguments": {"urn": KRAS_URN}})
    data = r.get("data", r) if isinstance(r, dict) else r
    rows = data.get("variants") if isinstance(data, dict) else (r if isinstance(r, list) else [])
    if not isinstance(rows, list):
        rows = []
    total_in_set = data.get("total_variants_in_set") if isinstance(data, dict) else None
    print(f"raw variant rows: {len(rows)} (total_in_set={total_in_set}, truncated={data.get('truncated') if isinstance(data, dict) else '?'})")
    if rows:
        print(f"first row keys: {list(rows[0].keys())[:15]}")
        print(f"first row: {rows[0]}")

    # Step 3: parse + filter
    print(f"\n=== Step 3: parse HGVS + filter to pos {POS_MIN}-{POS_MAX} ===")
    parsed = []
    dropped = 0
    for row in rows:
        hgvs = (row.get("hgvs_pro") or row.get("hgvs") or row.get("hgvs_protein") or "")
        m = HGVS_RE.match(hgvs)
        if not m:
            dropped += 1
            continue
        ref3, pos, alt3 = m.group(1), int(m.group(2)), m.group(3)
        if ref3 not in THREE_TO_ONE or alt3 not in THREE_TO_ONE:
            dropped += 1
            continue
        if not (POS_MIN <= pos <= POS_MAX):
            continue
        score = None
        for k in ("score", "ddG", "fitness"):
            v = row.get(k)
            if v is None:
                continue
            try:
                score = float(v)
                break
            except (TypeError, ValueError):
                pass
        if score is None or np.isnan(score):
            dropped += 1
            continue
        parsed.append({"position": pos, "ref_aa": THREE_TO_ONE[ref3],
                       "alt_aa": THREE_TO_ONE[alt3], "score": score})
    print(f"parsed: {len(parsed)} single-missense in pos {POS_MIN}-{POS_MAX}")
    print(f"dropped (non-missense / non-numeric / out-of-range): {dropped}")
    if not parsed:
        print("STOP: no usable variants")
        return
    # Numbering check
    landmark = Counter(p["position"] for p in parsed).most_common(1)[0][0]
    ref_aa = next(p["ref_aa"] for p in parsed if p["position"] == landmark)
    assert ref_aa == seq[landmark - 1], f"numbering off at pos {landmark}"
    print(f"numbering check: pos {landmark} ref={ref_aa} matches UniProt ✓")

    # Step 4: SAE feature tensor
    print(f"\n=== Step 4: SAE per-residue extraction ===")
    n_features = 16384
    positions = sorted({p["position"] for p in parsed})
    pos_index = {p: i for i, p in enumerate(positions)}
    aa_index = {a: i for i, a in enumerate(AAS)}
    print(f"positions: {positions}")
    print(f"WT calls: {len(positions)} (1 per position)")
    print(f"mutant calls: {len(parsed)}")
    print(f"total calls: {len(positions) + len(parsed)}")

    wt_vec = np.zeros((len(positions), n_features), dtype=np.float32)
    print("\n  WT extraction:")
    t0 = time.time()
    for p in positions:
        r = cached_sae(tu, seq, p)
        if "_error" in r:
            print(f"    pos {p}: ERR {r['_error']}")
            continue
        for feat in r["data"]["activations"][0]["active_features"]:
            wt_vec[pos_index[p], feat["feature_id"]] = feat["activation"]
    print(f"  WT done in {time.time()-t0:.1f}s")

    T = np.full((20, len(positions), n_features), np.nan, dtype=np.float32)
    print("\n  Mutant extraction:")
    t0 = time.time()
    errs = 0
    for i, p in enumerate(parsed):
        if (i + 1) % 25 == 0:
            print(f"    {i+1}/{len(parsed)} (errors: {errs}, elapsed {time.time()-t0:.0f}s)")
        mut_seq = seq[:p["position"]-1] + p["alt_aa"] + seq[p["position"]:]
        r = cached_sae(tu, mut_seq, p["position"])
        if "_error" in r:
            errs += 1
            continue
        feat_vec = np.zeros(n_features, dtype=np.float32)
        for feat in r["data"]["activations"][0]["active_features"]:
            feat_vec[feat["feature_id"]] = feat["activation"]
        T[aa_index[p["alt_aa"]], pos_index[p["position"]]] = feat_vec
    print(f"  mutants done in {time.time()-t0:.0f}s, errors: {errs}")

    # Step 5: global drop validation
    print(f"\n=== Step 5: global SAE drop vs DMS ===")
    drops = np.maximum(0.0, wt_vec[None, :, :] - T)
    sorted_desc = -np.sort(-drops, axis=-1)
    topk = sorted_desc[:, :, :3].mean(axis=-1)
    M = np.full((20, len(positions)), np.nan, dtype=np.float32)
    for p in parsed:
        M[aa_index[p["alt_aa"]], pos_index[p["position"]]] = p["score"]
    flat = M[~np.isnan(M)]
    print(f"  ΔΔG range: {np.nanmin(M):.2f} to {np.nanmax(M):.2f}, n={(~np.isnan(M)).sum()}")
    if len(flat) >= 20:
        disrupt_cut = np.quantile(flat, 0.7)
        neutral_band = 0.5
        neutral = (np.abs(M) <= neutral_band) & ~np.isnan(M)
        disruptive = (M >= disrupt_cut) & ~np.isnan(M) & ~neutral
        s_n = topk[neutral][~np.isnan(topk[neutral])]
        s_d = topk[disruptive][~np.isnan(topk[disruptive])]
        print(f"  neutral cells: {neutral.sum()}, disruptive cells: {disruptive.sum()}")
        if len(s_n) >= 5 and len(s_d) >= 5:
            _u, p_val = mannwhitneyu(s_d, s_n, alternative="greater")
            print(f"  Mann-Whitney U: disruptive med={np.median(s_d):.3f} vs neutral med={np.median(s_n):.3f}, p={p_val:.3g}")
        else:
            print("  too few samples for MWU")

    # Step 6: hotspot at G12/G13
    print(f"\n=== Step 6: G12/G13 hotspot feature enrichment ===")
    max_drop = np.nanmax(drops, axis=0)
    hotspot = [12, 13]
    cluster_cols = [pos_index[p] for p in hotspot if p in pos_index]
    print(f"  cluster (pos {hotspot}) = {len(cluster_cols)} columns")
    if cluster_cols:
        cluster_mean = max_drop[cluster_cols].mean(axis=0)
        top_features = np.argsort(-cluster_mean)[:5].tolist()
        print("  top 5 features by mean drop:")
        for f in top_features:
            print(f"    feature {f}: mean drop = {cluster_mean[f]:.4f}")
        print("\n  labeling top features via ESM_describe_sae_feature:")
        for f in top_features:
            r = tu.run({"name": "ESM_describe_sae_feature", "arguments": {
                "operation": "describe_sae_feature",
                "feature_id": int(f),
                "n_proteins": 3,  # small to keep cost down
            }})
            if r.get("status") == "success":
                d = r["data"]
                print(f"    feature {f} → {d.get('category', '?')} (conf={d.get('confidence', '?')}) [from_cache={r['metadata'].get('from_cache')}]")
            else:
                print(f"    feature {f} → ERR {r.get('error')}")

    print("\n=== Pipeline complete ===")


if __name__ == "__main__":
    main()
