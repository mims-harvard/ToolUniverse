"""Python normalizers for backends whose replies a declarative map cannot reach.

Most backends are handled entirely by ``output_map`` in
``data/unified_model_backends.json``. A handful are not, because the number the
canonical record needs is not a field in the reply at all -- it has to be
computed from the payload. Those name a function here.

Each function takes ``(payload, spec)`` and returns the canonical field dict.
It must not raise: a normalizer that throws turns one odd reply into a failed
benchmark run, so every path returns a dict and reports trouble in ``error``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def normalize_pdb_structure(payload: Any, spec: Any) -> Dict[str, Any]:
    """Read mean pLDDT out of raw PDB text.

    The NVIDIA NIM folding endpoints return a PDB file and no confidence
    summary. AlphaFold-family models write per-residue pLDDT into the
    B-factor column, so the summary statistic everyone quotes has to be
    recomputed from the coordinates -- once per residue, not per atom, or the
    mean is silently weighted by residue size (glycine has 4 backbone atoms,
    tryptophan 14).
    """
    text = _as_pdb_text(payload)
    if not text:
        return {"error": "Backend returned no PDB text.", "structure": None}

    per_residue: Dict[str, float] = {}
    for line in text.splitlines():
        if not line.startswith(("ATOM", "HETATM")):
            continue
        try:
            # Fixed-width PDB columns: chain 22, resSeq 23-26, B-factor 61-66.
            residue_key = line[21:27]
            bfactor = float(line[60:66])
        except (ValueError, IndexError):
            continue
        per_residue.setdefault(residue_key, bfactor)

    if not per_residue:
        return {
            "error": "PDB text carried no parsable B-factor column, so pLDDT is unavailable.",
            "structure": text,
            "format": "pdb",
        }

    values = list(per_residue.values())
    mean = sum(values) / len(values)
    # Some services write pLDDT on 0-1 and some on 0-100. Detect rather than
    # assume: a mean at or below 1.0 can only be the fractional scale.
    if mean <= 1.0:
        values = [v * 100 for v in values]
        mean *= 100

    return {
        "structure": text,
        "format": "pdb",
        "mean_plddt": round(mean, 2),
        "score": round(mean, 2),
        "n_residues": len(values),
        "confident_fraction": round(sum(1 for v in values if v >= 70) / len(values), 4),
    }


def normalize_boltz_structure(payload: Any, spec: Any) -> Dict[str, Any]:
    """Pull structure and confidence out of a Boltz-2 (NVIDIA NIM) reply.

    Field names and nesting here come from a real NIM response, not from the
    docs. The shape this code originally guessed at was wrong in three
    independent ways, and each one produced a plausible-looking
    ``{"structure": None}`` rather than an error a caller would notice:

    * the payload arrives inside ToolUniverse's ``{"status", "data"}``
      envelope, so nothing sits at the top level where it was being sought;
    * the confidence fields are *plural lists* -- ``complex_plddt_scores``,
      ``ptm_scores`` -- not the singular scalars that were expected;
    * coordinates live at ``data.structures[0].structure``, with the format
      declared beside them, not under a ``cif``/``pdb`` key.

    Observed for a 33-residue monomer: ``complex_plddt_scores [0.8838]``,
    ``confidence_scores [0.7071]``, ``ptm_scores [0.6527]``, ``format
    "mmcif"``. pLDDT arrives on 0-1 and is lifted to the 0-100 scale this
    task's canonical output uses.
    """
    if not isinstance(payload, dict):
        text = _as_pdb_text(payload)
        if text:
            return normalize_pdb_structure(text, spec)
        return {"error": "Boltz returned an unrecognized payload.", "structure": None}

    # Unwrap the envelope, tolerating an already-unwrapped body.
    body = payload.get("data") if isinstance(payload.get("data"), dict) else payload

    structure = None
    fmt = None
    entries = body.get("structures")
    if isinstance(entries, list) and entries:
        first = entries[0]
        if isinstance(first, dict):
            structure = _first_present(
                first, ("structure", "cif", "mmcif", "pdb", "content")
            )
            fmt = first.get("format")
        elif isinstance(first, str):
            structure = first
    if structure is None:
        structure = _first_present(
            body, ("structure", "cif", "mmcif", "output_cif", "pdb")
        )

    plddt = _scalar(
        _first_present(
            body,
            (
                "complex_plddt_scores",
                "complex_plddt",
                "plddt_scores",
                "plddt",
                "mean_plddt",
            ),
        )
    )
    confidence = _scalar(
        _first_present(body, ("confidence_scores", "confidence_score"))
    )
    if plddt is None:
        # Fall back to overall confidence only when no pLDDT was reported at
        # all; they are different quantities and must not be conflated.
        plddt = confidence
    if isinstance(plddt, (int, float)) and plddt <= 1.0:
        plddt = plddt * 100

    fields: Dict[str, Any] = {"structure": structure}
    if fmt:
        fields["format"] = (
            "mmcif" if str(fmt).lower() in ("mmcif", "cif") else str(fmt).lower()
        )
    else:
        fields["format"] = (
            "mmcif" if structure and "_atom_site" in str(structure)[:4000] else "pdb"
        )

    if isinstance(plddt, (int, float)):
        fields["mean_plddt"] = round(float(plddt), 2)
        fields["score"] = round(float(plddt), 2)
    else:
        fields["error"] = "Boltz reply carried no confidence score."

    if isinstance(confidence, (int, float)):
        fields["confidence_score"] = round(float(confidence), 4)
    for name, keys in (
        ("ptm", ("ptm_scores", "ptm", "ptm_score")),
        ("iptm", ("iptm_scores", "iptm")),
    ):
        value = _scalar(_first_present(body, keys))
        if isinstance(value, (int, float)):
            fields[name] = round(float(value), 4)

    affinities = body.get("affinities")
    if isinstance(affinities, dict) and affinities:
        fields["affinities"] = affinities
    return fields


def _scalar(value: Any) -> Any:
    """Collapse Boltz's one-entry-per-model lists to a single number."""
    if isinstance(value, list):
        numbers = [v for v in value if isinstance(v, (int, float))]
        if not numbers:
            return None
        return sum(numbers) / len(numbers)
    return value


def normalize_vep_predictor(payload: Any, spec: Any) -> Dict[str, Any]:
    """Read one predictor (SIFT, PolyPhen-2) out of a VEP annotation.

    VEP reports every overlapping transcript and the predictors are *sparse
    and inconsistent* across them. Confirmed live for TP53 R175H: of twelve
    transcripts, all but one carry a SIFT score but only two carry PolyPhen-2.
    Fixing on a single transcript therefore loses PolyPhen-2 entirely, which
    surfaced as "PolyPhen-2 returned no score" -- indistinguishable from the
    variant genuinely being absent from its table.

    The rule, applied per predictor rather than per transcript: prefer the
    MANE Select / canonical transcript when VEP flags one (it often does not,
    as in that same reply), otherwise take the most damaging value across
    protein-coding transcripts. Most-damaging matches the convention already
    used for dbNSFP's per-transcript arrays, and the transcript actually used
    is reported so the number can be traced.
    """
    params = getattr(spec, "params", {}) or {}
    score_field = params.get("score_field")
    pred_field = params.get("pred_field")
    pick = params.get("pick", "max")

    consequences = []
    if isinstance(payload, dict):
        consequences = payload.get("transcript_consequences") or []
    if not consequences:
        return {"error": "VEP returned no transcript consequences."}

    candidates = [
        c
        for c in consequences
        if isinstance(c, dict) and c.get(score_field) is not None
    ]
    if not candidates:
        return {
            "error": (
                f"VEP carried no {score_field} on any of the "
                f"{len(consequences)} transcripts for this variant."
            )
        }

    chosen = None
    for flag in ("mane_select", "canonical"):
        flagged = [c for c in candidates if c.get(flag)]
        if flagged:
            chosen = flagged[0]
            break
    if chosen is None:
        coding = [
            c for c in candidates if c.get("biotype") == "protein_coding"
        ] or candidates
        chosen = (min if pick == "min" else max)(
            coding, key=lambda c: float(c[score_field])
        )

    return {
        "score": float(chosen[score_field]),
        "classification": chosen.get(pred_field),
        "transcript": chosen.get("transcript_id"),
        "gene": chosen.get("gene_symbol"),
        "protein_position": chosen.get("protein_start"),
        "n_transcripts_with_score": len(candidates),
        "n_transcripts_total": len(consequences),
        "transcript_selection": (
            "MANE/canonical"
            if chosen.get("mane_select") or chosen.get("canonical")
            else f"most damaging of {len(candidates)} scored transcripts"
        ),
    }


# --------------------------------------------------------------------------- #
def _as_pdb_text(payload: Any) -> Optional[str]:
    """Find PDB coordinate text anywhere in a reply.

    Named keys are tried first, then *every* value is scanned. That fallback is
    load-bearing, not defensive padding: each NIM model nests its coordinates
    differently and the names are not documented together.
    ``NvidiaNIM_esmfold`` documents a top-level ``structure`` key, while a live
    ``NvidiaNIM_openfold2`` reply puts five ranked models at
    ``data.structures_in_ranked_order[*].structure``. A name-only lookup
    returned "Backend returned no PDB text" for OpenFold2 -- indistinguishable
    from the model having failed, when in fact a perfectly good structure had
    been returned and simply not found.

    Lists are walked in order, so a ranked model list yields rank 1.
    """
    if isinstance(payload, str):
        return payload if "ATOM  " in payload or payload.startswith("ATOM") else None

    if isinstance(payload, list):
        for item in payload:
            found = _as_pdb_text(item)
            if found:
                return found
        return None

    if isinstance(payload, dict):
        # Preferred names first, so a reply carrying several candidates yields
        # the one the service calls its answer.
        for key in ("structure", "pdb", "pdbs", "data", "output", "result", "content"):
            if key in payload:
                found = _as_pdb_text(payload[key])
                if found:
                    return found
        # Then anything else, for the shapes no one wrote down.
        for key, value in payload.items():
            if key in (
                "structure",
                "pdb",
                "pdbs",
                "data",
                "output",
                "result",
                "content",
            ):
                continue
            if isinstance(value, (str, list, dict)):
                found = _as_pdb_text(value)
                if found:
                    return found
    return None


def _first_present(payload: Dict[str, Any], keys: tuple) -> Any:
    for key in keys:
        if payload.get(key) is not None:
            return payload[key]
    return None
