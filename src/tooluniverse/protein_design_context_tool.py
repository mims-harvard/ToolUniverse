"""Local matched-backbone ablation of conditional sequence preferences."""

import hashlib
import json
import math
import re
from collections import defaultdict
from statistics import fmean

from .base_tool import BaseTool
from .tool_registry import register_tool

AMINO_ACIDS = frozenset("ACDEFGHIKLMNPQRSTVWY")


def _text(value, label):
    if not isinstance(value, str) or not value.strip() or len(value) > 200:
        raise ValueError(f"{label} must be a nonempty string of at most 200 characters")
    return value


def _sha(value, label):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _position(value):
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 1 <= value <= 100000
    ):
        raise ValueError("positions must be ligand sequence indices from 1 to 100000")
    return value


def _state(state, label, present, position, alphabet, parent, mutant):
    if not isinstance(state, dict) or state.get("receptor_present") is not present:
        raise ValueError(f"{label}.receptor_present must be {present}")
    identity = tuple(
        _sha(state.get(key), f"{label}.{key}")
        for key in (
            "ligand_backbone_sha256",
            "ligand_sequence_sha256",
            "protocol_sha256",
        )
    )
    mask = state.get("design_positions")
    if not isinstance(mask, list) or not 1 <= len(mask) <= 10000:
        raise ValueError(
            f"{label}.design_positions must be the explicit effective mask"
        )
    mask = tuple(sorted(_position(p) for p in mask))
    if len(set(mask)) != len(mask) or position not in mask:
        raise ValueError(
            f"{label}: selected position must occur once in the effective mask"
        )
    samples = state.get("log_probabilities")
    if not isinstance(samples, list) or not 1 <= len(samples) <= 100:
        raise ValueError(
            f"{label}.log_probabilities must have 1 to 100 decoding samples"
        )
    deltas = []
    for values in samples:
        if not isinstance(values, list) or len(values) != len(alphabet):
            raise ValueError(f"{label}: each sample must cover the declared alphabet")
        if any(
            isinstance(x, bool)
            or not isinstance(x, (int, float))
            or not math.isfinite(x)
            or x > 0
            for x in values
        ):
            raise ValueError(
                f"{label}: log probabilities must be finite and nonpositive"
            )
        maximum = max(values)
        log_total = maximum + math.log(math.fsum(math.exp(x - maximum) for x in values))
        if abs(log_total) > 1e-5:
            raise ValueError(
                f"{label}: probabilities must normalize over the full alphabet; "
                "zero placeholder rows, logits and partial alphabets are invalid"
            )
        delta = values[alphabet.index(mutant)] - values[alphabet.index(parent)]
        if not math.isfinite(delta):
            raise ValueError(
                f"{label}: mutation delta overflow; inspect the supplied scores"
            )
        deltas.append(delta)
    return identity, mask, deltas


@register_tool("ProteinDesignContextTool")
class ProteinDesignContextTool(BaseTool):
    """Postprocess declared matched receptor-present/deleted probability rows."""

    def run(self, arguments):
        try:
            return {"status": "success", "data": self._compare(arguments)}
        except (ValueError, TypeError, KeyError, OverflowError) as exc:
            return {"status": "error", "error": str(exc)}

    def _compare(self, args):
        if not isinstance(args, dict):
            raise ValueError("arguments must be an object")
        position = _position(args.get("position"))
        parent, mutant = args.get("parent_residue"), args.get("mutant_residue")
        if any(
            not isinstance(x, str) or x not in AMINO_ACIDS for x in (parent, mutant)
        ):
            raise ValueError(
                "parent_residue and mutant_residue must be canonical amino acids"
            )
        if parent == mutant:
            raise ValueError("mutant_residue must differ from parent_residue")
        alphabet = args.get("alphabet")
        if (
            not isinstance(alphabet, str)
            or len(set(alphabet)) != len(alphabet)
            or set(alphabet) not in (AMINO_ACIDS, AMINO_ACIDS | {"X"})
        ):
            raise ValueError(
                "alphabet must contain all 20 amino acids, optionally X, once each"
            )
        if args.get("scoring_mode") != "conditional_on_other_residues":
            raise ValueError(
                "use conditional_on_other_residues; unconditional scores are out of scope"
            )
        scorer = _text(args.get("scorer_family"), "scorer_family")
        poses = args.get("expected_poses")
        checkpoints = args.get("expected_checkpoints")
        if not isinstance(poses, list) or not 1 <= len(poses) <= 128:
            raise ValueError(
                "expected_poses must declare 1 to 128 coordinate-unique poses"
            )
        pose_keys = set()
        for pose in poses:
            if not isinstance(pose, dict):
                raise ValueError("expected_poses entries must be objects")
            key = (
                _text(pose.get("source_family"), "source_family"),
                _sha(pose.get("pose_sha256"), "pose_sha256"),
            )
            if key in pose_keys:
                raise ValueError(
                    "duplicate expected pose; resolve coordinate aliases before analysis"
                )
            pose_keys.add(key)
        if not isinstance(checkpoints, list) or not 1 <= len(checkpoints) <= 8:
            raise ValueError(
                "expected_checkpoints must declare 1 to 8 scorer checkpoint digests"
            )
        checkpoints = [_sha(c, "expected_checkpoints") for c in checkpoints]
        if len(set(checkpoints)) != len(checkpoints):
            raise ValueError("duplicate scorer checkpoint")
        expected = {(f, p, c) for f, p in pose_keys for c in checkpoints}
        contexts = args.get("contexts")
        if not isinstance(contexts, list) or len(contexts) != len(expected):
            raise ValueError(
                "contexts must cover every declared pose/checkpoint pair exactly once"
            )
        seen, rows, groups = set(), [], defaultdict(list)
        common_identity = None
        pose_backbones = {}
        for context in contexts:
            if not isinstance(context, dict):
                raise ValueError("contexts entries must be objects")
            key = (
                _text(context.get("source_family"), "source_family"),
                _sha(context.get("pose_sha256"), "pose_sha256"),
                _sha(context.get("checkpoint_sha256"), "checkpoint_sha256"),
            )
            if key not in expected or key in seen:
                raise ValueError(
                    "unexpected or duplicate pose/checkpoint pair; inspect coverage"
                )
            seen.add(key)
            full = _state(
                context.get("full_complex"),
                "full_complex",
                True,
                position,
                alphabet,
                parent,
                mutant,
            )
            deleted = _state(
                context.get("receptor_deleted"),
                "receptor_deleted",
                False,
                position,
                alphabet,
                parent,
                mutant,
            )
            if full[:2] != deleted[:2]:
                raise ValueError(
                    "matched pair must retain identical ligand backbone, sequence, protocol and mask"
                )
            identity = (full[0][1:], full[1])
            if common_identity is not None and identity != common_identity:
                raise ValueError(
                    "all contexts must share ligand sequence, protocol and effective design mask"
                )
            common_identity = identity
            if key[:2] in pose_backbones and pose_backbones[key[:2]] != full[0][0]:
                raise ValueError(
                    "the same pose must retain its ligand backbone across checkpoints"
                )
            pose_backbones[key[:2]] = full[0][0]
            a, b = full[2], deleted[2]
            low, high = min(a) - max(b), max(a) - min(b)
            effect = fmean(a) - fmean(b)
            if not all(math.isfinite(v) for v in (low, high, effect)):
                raise ValueError("context effect overflow; inspect the supplied scores")
            row = {
                "source_family": key[0],
                "pose_sha256": key[1],
                "checkpoint_sha256": key[2],
                "full_mutation_delta_nats": a,
                "deleted_mutation_delta_nats": b,
                "full_mean_delta_nats": fmean(a),
                "deleted_mean_delta_nats": fmean(b),
                "receptor_context_effect_nats": effect,
                "unpaired_sample_range_nats": [low, high],
            }
            rows.append(row)
            groups[(key[0], key[2])].append(row)
        summaries = []
        for (family, checkpoint), values in sorted(groups.items()):
            lows = [v["unpaired_sample_range_nats"][0] for v in values]
            highs = [v["unpaired_sample_range_nats"][1] for v in values]
            summaries.append(
                {
                    "source_family": family,
                    "checkpoint_sha256": checkpoint,
                    "pose_count": len(values),
                    "equal_pose_mean_context_effect_nats": fmean(
                        v["receptor_context_effect_nats"] for v in values
                    ),
                    "all_pose_sample_ranges_positive": all(v > 0 for v in lows),
                    "all_pose_sample_ranges_negative": all(v < 0 for v in highs),
                }
            )
        return {
            "rows": sorted(
                rows,
                key=lambda r: (
                    r["source_family"],
                    r["pose_sha256"],
                    r["checkpoint_sha256"],
                ),
            ),
            "family_checkpoint_summary": summaries,
            "coverage": {
                "declared_pose_count": len(pose_keys),
                "source_family_count": len({f for f, _ in pose_keys}),
                "scorer_family": scorer,
                "scorer_family_count": 1,
                "checkpoint_count": len(checkpoints),
                "matched_context_count": len(rows),
                "declared_matrix_complete": seen == expected,
            },
            "input_sha256": hashlib.sha256(
                json.dumps(args, sort_keys=True, allow_nan=False).encode()
            ).hexdigest(),
            "coordinate_identity_verified": False,
            "binding_verified": False,
            "limitations": [
                "Caller-supplied hashes, masks, receptor presence and source-family labels are declarations; coordinates are not inspected.",
                "A positive effect is a learned receptor-context preference on fixed geometry, not binding free energy, KD, pose probability or activation.",
                "Decoding samples are unpaired; the sample range is not a confidence interval. Equal numeric seeds do not imply shared random noise.",
                "Related checkpoints remain one scorer family. Matrix completeness covers only the caller-declared poses and checkpoints.",
            ],
        }
