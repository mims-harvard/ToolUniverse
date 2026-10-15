"""Benchmark metrics for the unified model interface.

Two decisions here shape every number the leaderboard reports.

**Rank metrics run on the native score, never on ``normalized_score``.**
Several backends are normalized with a calibration we chose ourselves (see
``calibration: "heuristic"`` in the backend registry). If AUROC were computed
on the normalized value, re-tuning a logistic midpoint could reorder the
leaderboard without any model changing, which would make the benchmark measure
our config instead of the models. AUROC, AUPRC, Spearman and Pearson therefore
take the raw score plus a direction flag and nothing else. Only the
threshold-dependent metrics -- accuracy, MCC, F1 -- depend on a cutoff, and
those use each backend's *own published or declared* threshold, reported
alongside the result.

**Every metric is reported with the n it was computed on.** Backends cover
different subsets of any real dataset: precomputed predictors miss variants
absent from their tables, and coordinate-keyed models skip anything that will
not resolve. A model that scores 40% of a set can post a flattering AUROC on
the easy remainder, so ``coverage`` is a first-class metric and no aggregate is
shown without the denominator that produced it.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

# scipy is an optional extra, and only the two rank metrics need it. Importing
# it at the top of a function hid that from `test_extras.py`'s guard check: a
# machine without the extra got an ImportError in the middle of a benchmark run
# instead of a metric reported as unavailable. Spearman and Pearson now return
# None without it, which is the same thing they return when the overlap is too
# small -- and `coverage` and `n` are reported beside every metric, so a None
# is never mistaken for a score.
try:
    from scipy import stats as _scipy_stats

    HAS_SCIPY = True
except ImportError:  # pragma: no cover - depends on the installed extras
    _scipy_stats = None
    HAS_SCIPY = False

CLASSIFICATION_METRICS = (
    "auroc",
    "auprc",
    "accuracy",
    "mcc",
    "f1",
    "precision",
    "recall",
)
REGRESSION_METRICS = ("spearman", "pearson", "rmse", "mae", "r2")
ALWAYS = ("coverage", "n", "latency")


def _ranks(values: np.ndarray) -> np.ndarray:
    """Average ranks, so that tied scores cannot inflate a rank statistic.

    Ties are not an edge case here: a predictor that returns 0.0 for every
    benign variant produces hundreds of them, and assigning those arbitrary
    distinct ranks would manufacture discrimination the model does not have.
    """
    order = np.argsort(values, kind="mergesort")
    ranked = np.empty(len(values), dtype=float)
    ranked[order] = np.arange(1, len(values) + 1, dtype=float)
    sorted_values = values[order]
    i = 0
    while i < len(sorted_values):
        j = i
        while j + 1 < len(sorted_values) and sorted_values[j + 1] == sorted_values[i]:
            j += 1
        if j > i:
            ranked[order[i : j + 1]] = (i + 1 + j + 1) / 2.0
        i = j + 1
    return ranked


def auroc(
    scores: Sequence[float], labels: Sequence[int], higher_is_positive: bool = True
) -> Optional[float]:
    """Area under the ROC curve, via the Mann-Whitney U identity (tie-aware)."""
    s, y = _clean_pairs(scores, labels)
    if s is None:
        return None
    if not higher_is_positive:
        s = -s
    n_pos = int(y.sum())
    n_neg = len(y) - n_pos
    if n_pos == 0 or n_neg == 0:
        return None
    r = _ranks(s)
    return float((r[y == 1].sum() - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg))


def auprc(
    scores: Sequence[float], labels: Sequence[int], higher_is_positive: bool = True
) -> Optional[float]:
    """Average precision.

    Uses the step-wise sum (the `average_precision_score` definition) rather
    than trapezoidal interpolation, which is optimistically biased on the
    small, heavily imbalanced label sets these benchmarks produce.
    """
    s, y = _clean_pairs(scores, labels)
    if s is None:
        return None
    if not higher_is_positive:
        s = -s
    n_pos = int(y.sum())
    if n_pos == 0:
        return None

    order = np.argsort(-s, kind="mergesort")
    y = y[order]
    tp = np.cumsum(y)
    precision = tp / np.arange(1, len(y) + 1)
    return float((precision * y).sum() / n_pos)


def confusion(
    calls: Sequence[Any], labels: Sequence[int], positive_call: str
) -> Optional[Dict[str, int]]:
    pairs = [
        (call, label)
        for call, label in zip(calls, labels)
        if call is not None and label is not None and str(call) != "uncertain"
    ]
    if not pairs:
        return None
    tp = fp = tn = fn = 0
    for call, label in pairs:
        predicted = str(call) == positive_call
        actual = bool(label)
        if predicted and actual:
            tp += 1
        elif predicted and not actual:
            fp += 1
        elif not predicted and actual:
            fn += 1
        else:
            tn += 1
    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn, "n": len(pairs)}


def from_confusion(cm: Optional[Dict[str, int]]) -> Dict[str, Optional[float]]:
    if not cm:
        return {
            "accuracy": None,
            "mcc": None,
            "f1": None,
            "precision": None,
            "recall": None,
        }
    tp, fp, tn, fn = cm["tp"], cm["fp"], cm["tn"], cm["fn"]
    total = tp + fp + tn + fn
    precision = tp / (tp + fp) if (tp + fp) else None
    recall = tp / (tp + fn) if (tp + fn) else None
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and (precision + recall) > 0
        else None
    )
    denominator = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    mcc = ((tp * tn) - (fp * fn)) / denominator if denominator else None
    return {
        "accuracy": (tp + tn) / total if total else None,
        "mcc": mcc,
        "f1": f1,
        "precision": precision,
        "recall": recall,
    }


def spearman(
    scores: Sequence[float], truth: Sequence[float], higher_is_positive: bool = True
) -> Optional[float]:
    s, t = _clean_pairs(scores, truth, labels_are_binary=False)
    if s is None or len(s) < 3:
        return None
    if not higher_is_positive:
        s = -s
    if not HAS_SCIPY:
        return None

    rho = _scipy_stats.spearmanr(s, t).statistic
    return (
        None
        if rho is None or (isinstance(rho, float) and math.isnan(rho))
        else float(rho)
    )


def pearson(
    scores: Sequence[float], truth: Sequence[float], higher_is_positive: bool = True
) -> Optional[float]:
    s, t = _clean_pairs(scores, truth, labels_are_binary=False)
    if s is None or len(s) < 3:
        return None
    if not higher_is_positive:
        s = -s
    if not HAS_SCIPY:
        return None

    r = _scipy_stats.pearsonr(s, t).statistic
    return None if r is None or (isinstance(r, float) and math.isnan(r)) else float(r)


def rmse(predictions: Sequence[float], truth: Sequence[float]) -> Optional[float]:
    p, t = _clean_pairs(predictions, truth, labels_are_binary=False)
    if p is None:
        return None
    return float(np.sqrt(np.mean((p - t) ** 2)))


def mae(predictions: Sequence[float], truth: Sequence[float]) -> Optional[float]:
    p, t = _clean_pairs(predictions, truth, labels_are_binary=False)
    if p is None:
        return None
    return float(np.mean(np.abs(p - t)))


def r2(predictions: Sequence[float], truth: Sequence[float]) -> Optional[float]:
    p, t = _clean_pairs(predictions, truth, labels_are_binary=False)
    if p is None or len(p) < 2:
        return None
    ss_res = float(np.sum((t - p) ** 2))
    ss_tot = float(np.sum((t - np.mean(t)) ** 2))
    return None if ss_tot == 0 else 1.0 - ss_res / ss_tot


def _clean_pairs(
    scores: Sequence[Any], labels: Sequence[Any], labels_are_binary: bool = True
) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    """Keep only the items where both a score and a label are present.

    Dropping unmatched items silently is exactly what makes a partial-coverage
    model look good, which is why every caller pairs the metric it gets back
    with the ``coverage`` figure computed from the same pass.
    """
    pairs = []
    for score, label in zip(scores, labels):
        if score is None or label is None:
            continue
        try:
            score_value = float(score)
            label_value = float(label)
        except (TypeError, ValueError):
            continue
        if (
            math.isnan(score_value)
            or math.isnan(label_value)
            or math.isinf(score_value)
        ):
            continue
        pairs.append((score_value, label_value))
    if not pairs:
        return None, None
    array = np.array(pairs, dtype=float)
    labels_out = array[:, 1]
    if labels_are_binary:
        labels_out = (labels_out > 0).astype(float)
    return array[:, 0], labels_out


def evaluate(
    records: List[Dict[str, Any]],
    labels: List[Any],
    higher_is_positive: Optional[bool],
    positive_call: str,
    task_type: str,
    n_total: int,
    requested: Optional[Sequence[str]] = None,
    continuous_labels: Optional[List[Any]] = None,
) -> Dict[str, Any]:
    """Score one backend's predictions over a dataset.

    ``records`` and ``labels`` are index-aligned and the same length as the
    dataset; a failed or skipped item is a ``None`` record, which is what makes
    ``coverage`` meaningful.
    """
    scores = [r.get("score") if r else None for r in records]
    calls = [r.get("call") if r else None for r in records]
    # A deep-mutational-scanning set carries the measured fitness alongside the
    # thresholded label, and ProteinGym itself ranks models on Spearman against
    # that continuous value. Correlating against the binarized label instead
    # throws away most of the signal and is not the published metric.
    rank_targets = continuous_labels if continuous_labels is not None else labels
    scored = sum(1 for s in scores if s is not None)
    latencies = [
        r.get("latency_s") for r in records if r and r.get("latency_s") is not None
    ]

    out: Dict[str, Any] = {
        "n": n_total,
        "n_scored": scored,
        "coverage": round(scored / n_total, 4) if n_total else 0.0,
        "latency_s_median": round(float(np.median(latencies)), 3)
        if latencies
        else None,
    }

    # Direction is unknown for categorical backends, so a rank metric would be
    # meaningless; report the threshold metrics for them and say why.
    if task_type in ("binary_score", "classification", "mixed"):
        if higher_is_positive is None:
            out["auroc"] = None
            out["auprc"] = None
            out["rank_metrics_note"] = (
                "This backend emits a class label, not an ordered score, so AUROC "
                "and AUPRC are undefined for it. Compare it on accuracy/MCC."
            )
        else:
            out["auroc"] = _round(auroc(scores, labels, higher_is_positive))
            out["auprc"] = _round(auprc(scores, labels, higher_is_positive))
        cm = confusion(calls, labels, positive_call)
        out["confusion"] = cm
        out.update({k: _round(v) for k, v in from_confusion(cm).items()})

    if task_type in ("regression", "mixed", "affinity", "binary_score"):
        direction = True if higher_is_positive is None else higher_is_positive
        out["spearman"] = _round(spearman(scores, rank_targets, direction))
        if continuous_labels is not None:
            out["spearman_target"] = "measured value (continuous)"
        if task_type in ("regression", "affinity", "mixed"):
            out["pearson"] = _round(pearson(scores, rank_targets, direction))
            out["rmse"] = _round(rmse(scores, rank_targets))
            out["mae"] = _round(mae(scores, rank_targets))
            out["r2"] = _round(r2(scores, rank_targets))

    if requested:
        keep = (
            set(requested)
            | set(ALWAYS)
            | {
                "confusion",
                "n_scored",
                "rank_metrics_note",
                "spearman_target",
            }
        )
        out = {k: v for k, v in out.items() if k in keep}
    return out


def _round(value: Optional[float], digits: int = 4) -> Optional[float]:
    return None if value is None else round(float(value), digits)


# --------------------------------------------------------------------------- #
# Structural accuracy
# --------------------------------------------------------------------------- #
# Predicted structures come with pLDDT, which is the model's own *confidence*,
# not its accuracy. Ranking folders by mean pLDDT rewards the confidently wrong
# over the honestly uncertain, so it cannot be a benchmark metric. lDDT is the
# measured counterpart: the quantity pLDDT is trained to predict, computed
# against an experimental reference.
#
# lDDT is chosen over TM-score and GDT here because it is **superposition
# free** -- it compares local inter-atomic distances rather than optimising a
# global alignment, so there is no iterative fitting step to get subtly wrong,
# and it stays meaningful for multi-domain proteins where a single rigid
# superposition is misleading.
#
# Mariani et al., Bioinformatics 2013.
_LDDT_THRESHOLDS = (0.5, 1.0, 2.0, 4.0)
_LDDT_INCLUSION_RADIUS = 15.0


def _parse_ca_mmcif(text: str) -> Dict[Any, Any]:
    """Cα coordinates from an mmCIF ``_atom_site`` loop.

    Needed because the co-folding models return mmCIF, not PDB: Boltz-2
    "succeeded" and then silently carried no lDDT at all, because the PDB
    fixed-column reader found zero atoms in it. Column order in mmCIF is
    declared by the loop header rather than fixed, so the header is read first
    instead of assuming positions.
    """
    lines = text.splitlines()
    coords: Dict[Any, Any] = {}
    i = 0
    while i < len(lines):
        if lines[i].strip() != "loop_":
            i += 1
            continue
        j = i + 1
        headers = []
        while j < len(lines) and lines[j].lstrip().startswith("_atom_site."):
            headers.append(lines[j].strip().split(".", 1)[1])
            j += 1
        if not headers:
            i = j + 1
            continue

        def idx(*names):
            for n in names:
                if n in headers:
                    return headers.index(n)
            return None

        c = {
            "group": idx("group_PDB"),
            "atom": idx("label_atom_id", "auth_atom_id"),
            "alt": idx("label_alt_id"),
            "chain": idx("auth_asym_id", "label_asym_id"),
            "seq": idx("auth_seq_id", "label_seq_id"),
            "x": idx("Cartn_x"),
            "y": idx("Cartn_y"),
            "z": idx("Cartn_z"),
            "model": idx("pdbx_PDB_model_num"),
        }
        if None in (c["atom"], c["chain"], c["seq"], c["x"], c["y"], c["z"]):
            i = j
            continue

        while j < len(lines):
            row = lines[j].strip()
            if not row or row.startswith(("#", "loop_", "_")):
                break
            f = row.split()
            j += 1
            if len(f) <= max(v for v in c.values() if v is not None):
                continue
            if c["group"] is not None and f[c["group"]] != "ATOM":
                continue
            if f[c["atom"]].strip('"') != "CA":
                continue
            if c["alt"] is not None and f[c["alt"]] not in (".", "?", "A"):
                continue
            # Only the first model, matching the PDB reader's behaviour.
            if c["model"] is not None and f[c["model"]] not in ("1", ".", "?"):
                continue
            try:
                key = (f[c["chain"]], int(f[c["seq"]]))
                coords[key] = (float(f[c["x"]]), float(f[c["y"]]), float(f[c["z"]]))
            except (ValueError, IndexError):
                continue
        i = j
    return coords


def parse_ca_coordinates(pdb_text: str) -> Dict[str, Any]:
    """Cα coordinates keyed by (chain, residue number) from PDB text.

    Only the first model of a multi-model file is read, and alternate
    locations other than the primary are skipped -- both would otherwise
    contribute duplicate residues and silently distort the distance set.
    """
    text = pdb_text or ""
    # Accept either format: the folders disagree about which they emit.
    if "_atom_site." in text[:20000]:
        return _parse_ca_mmcif(text)

    coords: Dict[Any, Any] = {}
    for line in text.splitlines():
        if line.startswith("ENDMDL"):
            break
        if not line.startswith("ATOM"):
            continue
        if line[12:16].strip() != "CA":
            continue
        altloc = line[16]
        if altloc not in (" ", "A"):
            continue
        try:
            key = (line[21], int(line[22:26]))
            coords[key] = (float(line[30:38]), float(line[38:46]), float(line[46:54]))
        except (ValueError, IndexError):
            continue
    return coords


def lddt(
    model_pdb: str,
    reference_pdb: str,
    inclusion_radius: float = _LDDT_INCLUSION_RADIUS,
) -> Optional[Dict[str, Any]]:
    """Cα lDDT of a predicted structure against a reference, in [0, 1].

    Residues are matched by (chain, residue number); only residues present in
    both are scored, and the fraction matched is returned alongside so a model
    cannot post a high score on a fragment. Returns ``None`` when there is not
    enough overlap to mean anything.
    """
    model = parse_ca_coordinates(model_pdb)
    reference = parse_ca_coordinates(reference_pdb)
    if not model or not reference:
        return None

    shared = sorted(set(model) & set(reference))
    if len(shared) < 4:
        return None

    m = np.array([model[k] for k in shared], dtype=float)
    r = np.array([reference[k] for k in shared], dtype=float)

    d_ref = np.linalg.norm(r[:, None, :] - r[None, :, :], axis=-1)
    d_mod = np.linalg.norm(m[:, None, :] - m[None, :, :], axis=-1)

    # Pairs the reference says are in contact, excluding self-pairs. Taking the
    # upper triangle counts each pair once.
    considered = (d_ref < inclusion_radius) & ~np.eye(len(shared), dtype=bool)
    considered = np.triu(considered)
    total = int(considered.sum())
    if total == 0:
        return None

    deviation = np.abs(d_mod - d_ref)[considered]
    preserved = [float((deviation < t).mean()) for t in _LDDT_THRESHOLDS]

    return {
        "lddt": round(float(np.mean(preserved)), 4),
        "per_threshold": {
            str(t): round(p, 4) for t, p in zip(_LDDT_THRESHOLDS, preserved)
        },
        "n_residues_scored": len(shared),
        "n_residues_reference": len(reference),
        "coverage": round(len(shared) / len(reference), 4),
        "n_pairs": total,
    }


# --------------------------------------------------------------------------- #
# Interface accuracy (DockQ)
# --------------------------------------------------------------------------- #
# lDDT judges a single chain's fold. It says nothing about whether two chains
# were docked together correctly, which is the question for complexes, binder
# design and docking -- and the reason those tasks could only report each
# model's own confidence in its own units.
#
# DockQ is the standard answer (Basu & Wallner, PLoS ONE 2016), combining three
# measures of interface quality into one 0-1 score:
#   Fnat  fraction of the reference's inter-chain residue contacts recovered
#   iRMS  backbone RMSD over interface residues after superposing them
#   LRMS  ligand-chain RMSD after superposing the receptor chain
# The published bands: >0.80 high, >0.49 medium, >0.23 acceptable, else wrong.
_DOCKQ_CONTACT_CUTOFF = 5.0
_DOCKQ_INTERFACE_CUTOFF = 10.0


def parse_atoms_by_chain(text: str) -> Dict[str, Dict[int, Dict[str, Any]]]:
    """Heavy atoms grouped as ``{chain: {residue_number: {atom_name: xyz}}}``.

    Hydrogens are dropped: contact definitions are heavy-atom based, and
    predicted structures vary in whether they carry hydrogens at all, so
    including them would make the score depend on the writer rather than the
    geometry.
    """
    out: Dict[str, Dict[int, Dict[str, Any]]] = {}
    for line in (text or "").splitlines():
        if line.startswith("ENDMDL"):
            break
        if not line.startswith("ATOM"):
            continue
        try:
            element = line[76:78].strip() or line[12:16].strip()[:1]
            if element.upper() == "H":
                continue
            altloc = line[16]
            if altloc not in (" ", "A"):
                continue
            chain = line[21]
            resnum = int(line[22:26])
            atom = line[12:16].strip()
            xyz = (float(line[30:38]), float(line[38:46]), float(line[46:54]))
        except (ValueError, IndexError):
            continue
        out.setdefault(chain, {}).setdefault(resnum, {})[atom] = xyz
    return out


def _kabsch_rmsd(mobile: np.ndarray, target: np.ndarray) -> float:
    """RMSD after optimal rigid superposition (Kabsch, with reflection guard)."""
    mc = mobile - mobile.mean(axis=0)
    tc = target - target.mean(axis=0)
    v, _, wt = np.linalg.svd(mc.T @ tc)
    # Without this the SVD can return a reflection, which superposes a mirror
    # image and reports an impossibly good fit.
    d = np.sign(np.linalg.det(v @ wt))
    rotation = v @ np.diag([1.0, 1.0, d]) @ wt
    aligned = mc @ rotation
    return float(np.sqrt(((aligned - tc) ** 2).sum(axis=1).mean()))


def _contacts(
    atoms: Dict[str, Dict[int, Dict[str, Any]]], rec: str, lig: str, cutoff: float
):
    """Inter-chain residue pairs with any heavy-atom pair within ``cutoff``."""
    r_res = sorted(atoms.get(rec, {}))
    l_res = sorted(atoms.get(lig, {}))
    if not r_res or not l_res:
        return set()
    r_pts, r_owner = [], []
    for rn in r_res:
        for xyz in atoms[rec][rn].values():
            r_pts.append(xyz)
            r_owner.append(rn)
    l_pts, l_owner = [], []
    for ln in l_res:
        for xyz in atoms[lig][ln].values():
            l_pts.append(xyz)
            l_owner.append(ln)
    R = np.array(r_pts)
    L = np.array(l_pts)
    close = np.linalg.norm(R[:, None, :] - L[None, :, :], axis=-1) < cutoff
    ro = np.array(r_owner)
    lo = np.array(l_owner)
    idx = np.argwhere(close)
    return {(int(ro[i]), int(lo[j])) for i, j in idx}


def dockq(
    model_pdb: str,
    reference_pdb: str,
    receptor_chain: Optional[str] = None,
    ligand_chain: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """DockQ score for a two-chain interface, in [0, 1].

    Chains default to the two largest in the reference. Only residues present
    in both structures are used, and the matched fraction is reported so a
    partial model cannot post a flattering score.
    """
    m_atoms = parse_atoms_by_chain(model_pdb)
    r_atoms = parse_atoms_by_chain(reference_pdb)
    if len(r_atoms) < 2 or len(m_atoms) < 2:
        return None

    if not (receptor_chain and ligand_chain):
        # Pick the pair with the LARGEST interface, not the two biggest chains.
        # Confirmed on 1BRS (barnase-barstar): chains A and B are both copies of
        # barnase, so "two largest" selected a crystal-packing contact rather
        # than the biological interface the structure is famous for.
        best, best_n = None, 0
        chains = sorted(r_atoms, key=lambda c: -len(r_atoms[c]))
        for i, a in enumerate(chains):
            for b in chains[i + 1 :]:
                n = len(_contacts(r_atoms, a, b, _DOCKQ_CONTACT_CUTOFF))
                if n > best_n:
                    best, best_n = (a, b), n
        if best is None:
            return None
        receptor_chain, ligand_chain = best
    if receptor_chain not in m_atoms or ligand_chain not in m_atoms:
        return None

    native = _contacts(r_atoms, receptor_chain, ligand_chain, _DOCKQ_CONTACT_CUTOFF)
    if not native:
        return None
    modelled = _contacts(m_atoms, receptor_chain, ligand_chain, _DOCKQ_CONTACT_CUTOFF)
    fnat = len(native & modelled) / len(native)

    def ca(atoms, chain, resnums):
        pts, kept = [], []
        for rn in resnums:
            xyz = atoms.get(chain, {}).get(rn, {}).get("CA")
            if xyz is not None:
                pts.append(xyz)
                kept.append(rn)
        return np.array(pts) if pts else np.empty((0, 3)), kept

    # Interface residues, taken from the reference's wider contact shell.
    wide = _contacts(r_atoms, receptor_chain, ligand_chain, _DOCKQ_INTERFACE_CUTOFF)
    i_rec = sorted({a for a, _ in wide})
    i_lig = sorted({b for _, b in wide})
    _, rk = ca(r_atoms, receptor_chain, i_rec)
    _, mk = ca(m_atoms, receptor_chain, i_rec)
    _, rlk = ca(r_atoms, ligand_chain, i_lig)
    _, mlk = ca(m_atoms, ligand_chain, i_lig)
    shared_r = [r for r in rk if r in set(mk)]
    shared_l = [r for r in rlk if r in set(mlk)]
    if len(shared_r) + len(shared_l) < 3:
        return None
    ref_i = np.vstack(
        [
            ca(r_atoms, receptor_chain, shared_r)[0],
            ca(r_atoms, ligand_chain, shared_l)[0],
        ]
    )
    mod_i = np.vstack(
        [
            ca(m_atoms, receptor_chain, shared_r)[0],
            ca(m_atoms, ligand_chain, shared_l)[0],
        ]
    )
    irms = _kabsch_rmsd(mod_i, ref_i)

    # LRMS: superpose on the receptor, then measure the ligand where it landed.
    all_rec = [
        r for r in sorted(r_atoms[receptor_chain]) if r in m_atoms[receptor_chain]
    ]
    all_lig = [r for r in sorted(r_atoms[ligand_chain]) if r in m_atoms[ligand_chain]]
    ref_r, _ = ca(r_atoms, receptor_chain, all_rec)
    mod_r, _ = ca(m_atoms, receptor_chain, all_rec)
    ref_l, _ = ca(r_atoms, ligand_chain, all_lig)
    mod_l, _ = ca(m_atoms, ligand_chain, all_lig)
    if len(ref_r) < 3 or len(ref_l) < 1:
        return None
    rc, mc = ref_r.mean(axis=0), mod_r.mean(axis=0)
    v, _, wt = np.linalg.svd((mod_r - mc).T @ (ref_r - rc))
    d = np.sign(np.linalg.det(v @ wt))
    rot = v @ np.diag([1.0, 1.0, d]) @ wt
    lrms = float(np.sqrt((((mod_l - mc) @ rot - (ref_l - rc)) ** 2).sum(axis=1).mean()))

    score = (
        fnat + 1.0 / (1.0 + (lrms / 8.5) ** 2) + 1.0 / (1.0 + (irms / 1.5) ** 2)
    ) / 3.0
    quality = (
        "high"
        if score > 0.80
        else "medium"
        if score > 0.49
        else "acceptable"
        if score > 0.23
        else "incorrect"
    )
    return {
        "dockq": round(score, 4),
        "quality": quality,
        "fnat": round(fnat, 4),
        "irms": round(irms, 3),
        "lrms": round(lrms, 3),
        "receptor_chain": receptor_chain,
        "ligand_chain": ligand_chain,
        "n_native_contacts": len(native),
        "interface_residues_matched": len(shared_r) + len(shared_l),
    }
