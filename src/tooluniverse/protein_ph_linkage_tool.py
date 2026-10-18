"""Reference-normalized independent-site linkage; never an affinity predictor."""

import hashlib
import json
import math

from .base_tool import BaseTool
from .tool_registry import register_tool

GROUP_TYPES = {"ASP", "GLU", "HIS", "LYS", "ARG", "CYS", "TYR", "N+", "C-"}
R_KCAL = 0.00198720425864083
LN10 = math.log(10.0)


def _number(value, label, lower, upper):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not lower <= value <= upper
    ):
        raise ValueError(f"{label} must be finite and between {lower} and {upper}")
    return float(value)


def _text(value, label, allow_empty=False):
    if (
        not isinstance(value, str)
        or len(value) > 200
        or (not allow_empty and not value.strip())
    ):
        raise ValueError(f"{label} must be a nonempty string of at most 200 characters")
    return value


def _inventory(rows, label, predicted=False):
    if not isinstance(rows, list) or not 1 <= len(rows) <= 2000:
        raise ValueError(f"{label} must contain 1 to 2000 explicitly expanded groups")
    result = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"{label} entries must be objects")
        chain = row.get("chain")
        if not isinstance(chain, str) or not 1 <= len(chain) <= 200:
            raise ValueError(
                f"{label}.chain must be an explicit nonempty chain identity; a single blank is valid"
            )
        residue = row.get("residue_number")
        if isinstance(residue, bool) or not isinstance(residue, int):
            raise ValueError(f"{label}.residue_number must be an integer")
        insertion = _text(
            row.get("insertion_code", ""), f"{label}.insertion_code", True
        )
        kind = row.get("group_type")
        if not isinstance(kind, str) or kind not in GROUP_TYPES:
            raise ValueError(
                f"{label}.group_type must be a normalized protein group; resolve COO from coordinates first"
            )
        key = (chain, residue, insertion, kind)
        if key in result:
            raise ValueError(f"{label} contains duplicate group identities")
        result[key] = (
            _number(row.get("pka"), f"{label}.pka", -1000, 1000)
            if predicted
            else _text(row.get("component"), f"{label}.component")
        )
    return result


def _softplus(x):
    return max(x, 0.0) + math.log1p(math.exp(-abs(x)))


def _fraction(pka, ph):
    x = LN10 * (pka - ph)
    e = math.exp(-abs(x))
    return 1.0 / (1.0 + e) if x >= 0 else e / (1.0 + e)


def _site_linkage(pka, ph, reference_ph):
    """ln Q(ph)-ln Q(reference), stably even far outside the pH window."""
    x = LN10 * (pka - ph)
    y = LN10 * (pka - reference_ph)
    if x > 0 and y > 0:
        return (
            LN10 * (reference_ph - ph)
            + math.log1p(math.exp(-x))
            - math.log1p(math.exp(-y))
        )
    return _softplus(x) - _softplus(y)


@register_tool("ProteinPHLinkageTool")
class ProteinPHLinkageTool(BaseTool):
    """Postprocess caller-supplied, identity-mapped pKa inventories locally."""

    def run(self, arguments):
        try:
            return {"status": "success", "data": self._calculate(arguments)}
        except (ValueError, TypeError, KeyError) as exc:
            return {"status": "error", "error": str(exc)}

    def _calculate(self, args):
        expected = _inventory(args.get("expected_groups"), "expected_groups")
        bound = _inventory(args.get("bound_groups"), "bound_groups", True)
        free = _inventory(args.get("free_groups"), "free_groups", True)
        for label, actual in (("bound_groups", bound), ("free_groups", free)):
            missing, extra = set(expected) - set(actual), set(actual) - set(expected)
            if missing or extra:
                raise ValueError(
                    f"{label} does not match supplied expected inventory: {len(missing)} missing, {len(extra)} extra; resolve coverage before integration"
                )
        mode = args.get("reference_kind")
        if mode not in {"independent_coordinates", "same_coordinate_components"}:
            raise ValueError(
                "reference_kind must be independent_coordinates or same_coordinate_components (both titrate)"
            )
        provenance = args.get("provenance")
        if not isinstance(provenance, dict):
            raise ValueError(
                "provenance must declare pka_method, inventory_source and reference_description"
            )
        provenance = {
            k: _text(provenance.get(k), f"provenance.{k}")
            for k in ("pka_method", "inventory_source", "reference_description")
        }
        phs = args.get("ph_values")
        if not isinstance(phs, list) or not 1 <= len(phs) <= 20:
            raise ValueError("ph_values must contain 1 to 20 pH values")
        phs = [_number(ph, "pH", 0, 14) for ph in phs]
        reference = _number(args.get("reference_ph"), "reference_ph", 0, 14)
        temperature_input = args.get("temperature_kelvin")
        temperature = _number(
            298.15 if temperature_input is None else temperature_input,
            "temperature_kelvin",
            200,
            400,
        )
        keys = sorted(expected)

        def summarize(selected, ph):
            ln_relative = math.fsum(
                _site_linkage(bound[k], ph, reference)
                - _site_linkage(free[k], ph, reference)
                for k in selected
            )
            return {
                "group_count": len(selected),
                "delta_proton_count_bound_minus_free": math.fsum(
                    _fraction(bound[k], ph) - _fraction(free[k], ph) for k in selected
                ),
                "relative_log10_association": ln_relative / LN10,
                "relative_linkage_energy_kcal_mol": -R_KCAL * temperature * ln_relative,
            }

        terminal = [k for k in keys if k[3] in {"N+", "C-"}]
        nonterminal = [k for k in keys if k[3] not in {"N+", "C-"}]
        components = {
            name: [k for k in keys if expected[k] == name]
            for name in sorted(set(expected.values()))
        }
        normalized = {
            "groups": [
                {
                    "identity": list(k),
                    "component": expected[k],
                    "bound_pka": bound[k],
                    "free_pka": free[k],
                }
                for k in keys
            ],
            "ph_values": phs,
            "reference_ph": reference,
            "temperature_kelvin": temperature,
            "reference_kind": mode,
            "provenance": provenance,
        }
        return {
            "reference_kind": mode,
            "reference_ph": reference,
            "temperature_kelvin": temperature,
            "convention": "Association: energy(pH)-energy(reference_ph); positive at acidic pH is a release-direction linkage term only. d(log10 K_assoc)/d(pH) = -delta_proton_count.",
            "inventory": {
                "group_count": len(keys),
                "component_counts": {n: len(ks) for n, ks in components.items()},
                "matches_supplied_expected_inventory": True,
                "structural_completeness_verified": False,
            },
            "curve": [
                {
                    "pH": ph,
                    "total": summarize(keys, ph),
                    "termini": summarize(terminal, ph),
                    "nonterminal_same_mask": summarize(nonterminal, ph),
                    "components": {
                        n: summarize(ks, ph) for n, ks in components.items()
                    },
                }
                for ph in phs
            ],
            "provenance": provenance,
            "calculation_sha256": hashlib.sha256(
                json.dumps(normalized, sort_keys=True, allow_nan=False).encode()
            ).hexdigest(),
            "binding_verified": False,
            "pH_selectivity_verified": False,
            "limitations": [
                "Caller-declared inventory closure does not verify coordinates, missing components, termini, disulfides, caps or molecular composition.",
                "Expand every molecular copy explicitly; normalize free identities to the bound numbering before calling. No automatic correspondence or stoichiometric inference.",
                "Independent monoprotic-site model only; excludes coupled microstates, conformational redistribution, ligand ionization and ionic-strength effects.",
                "Both reference kinds use titrating pKas. Same-coordinate components are not fixed protonation states.",
                "Terminal-excluded sums are sensitivity diagnostics, not a physically capped construct. Partial-site inventories do not represent the complete binding reaction.",
                "No absolute affinity, KD, experimental pH selectivity or calibrated success probability is inferred; learned energies must not be supplied as pKas.",
            ],
        }
