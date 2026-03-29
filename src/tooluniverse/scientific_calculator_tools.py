"""
Scientific Calculator Tools

General-purpose scientific calculators: DNA translation (reading frames),
molecular formula analysis, equilibrium solver, enzyme kinetics, and
statistical tests. All pure Python — no external dependencies.
"""

import math
import re
from functools import reduce
from math import gcd
from typing import Any, Dict, List, Optional

from .base_tool import BaseTool
from .tool_registry import register_tool

# ── Standard genetic codon table (NCBI Code 1) ──

CODON_TABLE = {
    "TTT": "F",
    "TTC": "F",
    "TTA": "L",
    "TTG": "L",
    "CTT": "L",
    "CTC": "L",
    "CTA": "L",
    "CTG": "L",
    "ATT": "I",
    "ATC": "I",
    "ATA": "I",
    "ATG": "M",
    "GTT": "V",
    "GTC": "V",
    "GTA": "V",
    "GTG": "V",
    "TCT": "S",
    "TCC": "S",
    "TCA": "S",
    "TCG": "S",
    "CCT": "P",
    "CCC": "P",
    "CCA": "P",
    "CCG": "P",
    "ACT": "T",
    "ACC": "T",
    "ACA": "T",
    "ACG": "T",
    "GCT": "A",
    "GCC": "A",
    "GCA": "A",
    "GCG": "A",
    "TAT": "Y",
    "TAC": "Y",
    "TAA": "*",
    "TAG": "*",
    "CAT": "H",
    "CAC": "H",
    "CAA": "Q",
    "CAG": "Q",
    "AAT": "N",
    "AAC": "N",
    "AAA": "K",
    "AAG": "K",
    "GAT": "D",
    "GAC": "D",
    "GAA": "E",
    "GAG": "E",
    "TGT": "C",
    "TGC": "C",
    "TGA": "*",
    "TGG": "W",
    "CGT": "R",
    "CGC": "R",
    "CGA": "R",
    "CGG": "R",
    "AGT": "S",
    "AGC": "S",
    "AGA": "R",
    "AGG": "R",
    "GGT": "G",
    "GGC": "G",
    "GGA": "G",
    "GGG": "G",
}

# ── Atomic masses ──

ATOMIC_MASS = {"C": 12.011, "H": 1.008, "O": 15.999, "N": 14.007}
ATOMIC_MASS_EXT = {
    **ATOMIC_MASS,
    "S": 32.06,
    "P": 30.974,
    "F": 18.998,
    "Cl": 35.45,
    "Br": 79.904,
    "I": 126.904,
}


# ── Helper functions ──


def _translate_frame(dna: str, frame: int) -> str:
    """Translate DNA from given frame offset (0, 1, or 2)."""
    protein = []
    for i in range(frame, len(dna) - 2, 3):
        codon = dna[i : i + 3]
        protein.append(CODON_TABLE.get(codon, "?"))
    return "".join(protein)


def _longest_orf(protein: str) -> str:
    """Find longest stretch without a stop codon."""
    segments = protein.split("*")
    return max(segments, key=len) if segments else protein


def _parse_formula(formula_str: str) -> Dict[str, int]:
    """Parse molecular formula string into element-count dict."""
    tokens = re.findall(r"([A-Z][a-z]?)(\d*)", formula_str)
    atoms: Dict[str, int] = {}
    for element, count in tokens:
        if not element:
            continue
        n = int(count) if count else 1
        atoms[element] = atoms.get(element, 0) + n
    return atoms


def _formula_str(atoms: Dict[str, int]) -> str:
    """Hill notation: C first, H second, then alphabetical."""
    order = [e for e in ("C", "H") if e in atoms]
    order += sorted(k for k in atoms if k not in ("C", "H"))
    return "".join(
        f"{e}{n if n > 1 else ''}" for e, n in ((e, atoms[e]) for e in order)
    )


def _igcd(values: List[int]) -> int:
    return reduce(gcd, values)


def _degrees_of_unsaturation(atoms: Dict[str, int]) -> float:
    C = atoms.get("C", 0)
    H = atoms.get("H", 0)
    N = atoms.get("N", 0)
    X = sum(atoms.get(x, 0) for x in ("F", "Cl", "Br", "I"))
    return (2 * C + 2 + N - H - X) / 2


def _interpret_dou(dou: float) -> str:
    if dou == 0:
        return "saturated, open-chain (no rings or double bonds)"
    hints = []
    if dou >= 4:
        hints.append("likely contains a benzene ring (4 DoU)")
    if dou >= 2:
        hints.append(
            "could have a triple bond, or two double bonds, or a ring + double bond"
        )
    if dou == 1:
        hints.append("one ring OR one double bond")
    return "; ".join(hints) if hints else f"DoU = {dou}"


def _elemental_composition(atoms: Dict[str, int]) -> Dict[str, Any]:
    total_mass = sum(n * ATOMIC_MASS_EXT.get(e, 0.0) for e, n in atoms.items())
    pcts = {
        e: round(n * ATOMIC_MASS_EXT.get(e, 0.0) / total_mass * 100, 2)
        for e, n in atoms.items()
    }
    return {"molar_mass": round(total_mass, 3), "percentages": pcts}


def _linreg(xs: List[float], ys: List[float]):
    """Simple linear regression. Returns (slope, intercept, r2)."""
    n = len(xs)
    sx = sum(xs)
    sy = sum(ys)
    sxx = sum(x * x for x in xs)
    sxy = sum(x * y for x, y in zip(xs, ys))
    denom = n * sxx - sx * sx
    if abs(denom) < 1e-30:
        raise ValueError("Degenerate data: all x values identical.")
    slope = (n * sxy - sx * sy) / denom
    intercept = (sy * sxx - sx * sxy) / denom
    y_mean = sy / n
    ss_tot = sum((y - y_mean) ** 2 for y in ys)
    ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return slope, intercept, r2


# ── Chi-square p-value via gamma function ──


def _regularized_gamma_upper(
    a: float, x: float, max_iter: int = 300, eps: float = 1e-12
) -> float:
    """Upper regularized incomplete gamma: Q(a, x) = 1 - P(a, x)."""
    if x < 0 or a <= 0:
        raise ValueError(f"Invalid arguments: a={a}, x={x}.")
    if x == 0:
        return 1.0
    log_gamma_a = math.lgamma(a)
    if x < a + 1.0:
        ap = a
        delta = 1.0 / a
        total = delta
        for _ in range(max_iter):
            ap += 1.0
            delta *= x / ap
            total += delta
            if abs(delta) < abs(total) * eps:
                break
        return 1.0 - math.exp(-x + a * math.log(x) - log_gamma_a) * total
    else:
        fpmin = 1e-300
        b_cf = x + 1.0 - a
        c = 1.0 / fpmin
        d = 1.0 / b_cf
        h = d
        for i in range(1, max_iter + 1):
            an = -i * (i - a)
            b_cf += 2.0
            d = an * d + b_cf
            if abs(d) < fpmin:
                d = fpmin
            c = b_cf + an / c
            if abs(c) < fpmin:
                c = fpmin
            d = 1.0 / d
            delta = d * c
            h *= delta
            if abs(delta - 1.0) < eps:
                break
        return math.exp(-x + a * math.log(x) - log_gamma_a) * h


def _chi_square_p_value(chi2: float, df: int) -> float:
    if df <= 0:
        raise ValueError(f"Degrees of freedom must be > 0 (got {df}).")
    if chi2 <= 0:
        return 1.0
    return _regularized_gamma_upper(df / 2.0, chi2 / 2.0)


# ── Fisher's exact test helpers ──


def _log_comb(n: int, k: int) -> float:
    if k < 0 or k > n:
        return float("-inf")
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def _hypergeometric_pmf(k: int, n1: int, n2: int, n: int) -> float:
    return math.exp(_log_comb(n1, k) + _log_comb(n2, n - k) - _log_comb(n1 + n2, n))


# ── Incomplete beta for t-distribution p-values ──


def _incomplete_beta_reg(
    x: float, a: float, b: float, max_iter: int = 300, eps: float = 1e-12
) -> float:
    """Regularized incomplete beta I_x(a, b) via continued fraction."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    ln_beta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    front = math.exp(a * math.log(x) + b * math.log(1 - x) - ln_beta)
    if x > (a + 1.0) / (a + b + 2.0):
        return 1.0 - _incomplete_beta_reg(1 - x, b, a, max_iter, eps)
    fpmin = 1e-300
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < fpmin:
        d = fpmin
    d = 1.0 / d
    h = d
    for m in range(1, max_iter + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return front * h / a


def _t_pvalue(t_stat: float, df: int) -> float:
    """Two-tailed p-value from t distribution."""
    if math.isnan(t_stat) or df <= 0:
        return float("nan")
    t2 = t_stat**2
    x_beta = df / (df + t2)
    return _incomplete_beta_reg(x_beta, df / 2.0, 0.5)


# ══════════════════════════════════════════════════════════════
# Tool class
# ══════════════════════════════════════════════════════════════


@register_tool("ScientificCalculatorTool")
class ScientificCalculatorTool(BaseTool):
    """
    General-purpose scientific calculators.

    No external API calls. Provides:
    - DNA translation in all 3 reading frames
    - Molecular formula analysis and combustion analysis
    - Chemical equilibrium solver (Ksp, complex formation, common-ion)
    - Enzyme kinetics (Km/Vmax, Hill, Ki)
    - Statistical tests (chi-square, Fisher, regression, t-test)
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        operation = arguments.get("operation")
        if not operation:
            return {"status": "error", "error": "Missing required parameter: operation"}

        handlers = {
            "translate_reading_frames": self._translate_reading_frames,
            "analyze_formula": self._analyze_formula,
            "combustion_analysis": self._combustion_analysis,
            "ksp_simple": self._ksp_simple,
            "ksp_complex": self._ksp_complex,
            "common_ion": self._common_ion,
            "michaelis_menten": self._michaelis_menten,
            "hill": self._hill,
            "inhibition": self._inhibition,
            "chi_square": self._chi_square,
            "fisher_exact": self._fisher_exact,
            "linear_regression": self._linear_regression,
            "t_test": self._t_test,
        }

        handler = handlers.get(operation)
        if not handler:
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}",
                "available_operations": list(handlers.keys()),
            }

        try:
            result = handler(arguments)
            # Wrap successful results in data envelope for return_schema validation
            if isinstance(result, dict) and result.get("status") == "success":
                payload = {k: v for k, v in result.items() if k != "status"}
                return {"status": "success", "data": payload}
            return result
        except Exception as e:
            return {"status": "error", "error": f"Operation failed: {str(e)}"}

    # ── Tool 1: DNA translation in reading frames ──

    def _translate_reading_frames(self, args: Dict[str, Any]) -> Dict[str, Any]:
        sequence = args.get("sequence", "")
        if not sequence or not sequence.strip():
            return {"status": "error", "error": "sequence is required"}
        dna = re.sub(r"[^ATGCatgc]", "", sequence).upper()
        if not dna:
            return {"status": "error", "error": "No valid DNA bases found in sequence."}

        frame_arg = str(args.get("frame") or "all")
        frames_to_do = [0, 1, 2] if frame_arg == "all" else [int(frame_arg) - 1]

        results = {}
        best_frame = 0
        best_orf = ""
        best_orf_len = 0

        for f in frames_to_do:
            protein = _translate_frame(dna, f)
            orf = _longest_orf(protein)
            results[f"frame_{f + 1}"] = {
                "protein": protein,
                "protein_length": len(protein),
                "longest_orf": orf,
                "longest_orf_length_aa": len(orf),
            }
            if len(orf) > best_orf_len:
                best_orf_len = len(orf)
                best_orf = orf
                best_frame = f + 1

        return {
            "status": "success",
            "sequence_length": len(dna),
            "frames": results,
            "best_frame": best_frame,
            "best_orf": best_orf,
            "best_orf_length_aa": best_orf_len,
        }

    # ── Tool 2: Molecular formula analysis ──

    def _analyze_formula(self, args: Dict[str, Any]) -> Dict[str, Any]:
        formula = args.get("formula")
        if not formula:
            return {
                "status": "error",
                "error": "formula is required for analyze_formula mode.",
            }

        atoms = _parse_formula(formula)
        if not atoms:
            return {"status": "error", "error": f"Could not parse formula '{formula}'."}

        comp = _elemental_composition(atoms)
        dou = _degrees_of_unsaturation(atoms)

        return {
            "status": "success",
            "formula": formula,
            "atoms": atoms,
            "molar_mass": comp["molar_mass"],
            "degrees_of_unsaturation": dou,
            "dou_interpretation": _interpret_dou(dou),
            "elemental_composition": comp["percentages"],
        }

    def _combustion_analysis(self, args: Dict[str, Any]) -> Dict[str, Any]:
        sample_g = args.get("sample_g")
        co2_g = args.get("CO2_g")
        h2o_g = args.get("H2O_g")
        n2_g = args.get("N2_g") or 0.0
        molar_mass = args.get("molar_mass")

        if sample_g is None or co2_g is None or h2o_g is None:
            return {
                "status": "error",
                "error": "sample_g, CO2_g, and H2O_g are all required.",
            }
        if sample_g <= 0:
            return {"status": "error", "error": "sample_g must be positive."}

        M = ATOMIC_MASS
        moles_C = co2_g / (M["C"] + 2 * M["O"])
        moles_H = h2o_g / (2 * M["H"] + M["O"]) * 2
        moles_N = (n2_g / (2 * M["N"])) * 2

        mass_accounted = moles_C * M["C"] + moles_H * M["H"] + moles_N * M["N"]
        mass_O = sample_g - mass_accounted
        moles_O = max(mass_O / M["O"], 0.0)

        present = {
            k: v
            for k, v in {"C": moles_C, "H": moles_H, "O": moles_O, "N": moles_N}.items()
            if v > 1e-6
        }
        min_moles = min(present.values())
        ratios = {k: v / min_moles for k, v in present.items()}

        best_denom = 1
        best_err = float("inf")
        for denom in range(1, 7):
            err = sum(abs(r * denom - round(r * denom)) for r in ratios.values())
            if err < best_err:
                best_err = err
                best_denom = denom

        scaled = {k: round(v * best_denom) for k, v in ratios.items()}
        g = _igcd(list(scaled.values()))
        empirical = {k: v // g for k, v in scaled.items()}
        emp_formula = _formula_str(empirical)
        emp_mass = sum(n * M.get(e, 0.0) for e, n in empirical.items())

        result: Dict[str, Any] = {
            "status": "success",
            "moles": {
                "C": round(moles_C, 6),
                "H": round(moles_H, 6),
                "O": round(moles_O, 6),
                "N": round(moles_N, 6),
            },
            "empirical_formula": emp_formula,
            "empirical_molar_mass": round(emp_mass, 3),
        }

        if molar_mass is not None:
            factor = round(molar_mass / emp_mass)
            mol_atoms = {k: v * factor for k, v in empirical.items()}
            mol_formula = _formula_str(mol_atoms)
            mol_mass = sum(n * M.get(e, 0.0) for e, n in mol_atoms.items())
            dou = _degrees_of_unsaturation(mol_atoms)
            comp = _elemental_composition(mol_atoms)
            result.update(
                {
                    "scale_factor": factor,
                    "molecular_formula": mol_formula,
                    "molecular_molar_mass": round(mol_mass, 3),
                    "degrees_of_unsaturation": dou,
                    "dou_interpretation": _interpret_dou(dou),
                    "elemental_composition": comp["percentages"],
                }
            )
        else:
            dou = _degrees_of_unsaturation(empirical)
            comp = _elemental_composition(empirical)
            result.update(
                {
                    "formula": emp_formula,
                    "molar_mass": round(emp_mass, 3),
                    "degrees_of_unsaturation": dou,
                    "dou_interpretation": _interpret_dou(dou),
                    "elemental_composition": comp["percentages"],
                }
            )

        return result

    # ── Tool 3: Equilibrium solver ──

    def _ksp_simple(self, args: Dict[str, Any]) -> Dict[str, Any]:
        ksp = args.get("Ksp")
        if ksp is None:
            return {"status": "error", "error": "Ksp is required."}
        a = args.get("stoich_cation") or 1
        b = args.get("stoich_anion") or 1

        coeff = (a**a) * (b**b)
        n = a + b
        s = (ksp / coeff) ** (1.0 / n)

        return {
            "status": "success",
            "problem_type": "ksp_simple",
            "solubility_mol_per_L": s,
            "cation_conc": a * s,
            "anion_conc": b * s,
            "expression": f"Ksp = ({a}s)^{a} * ({b}s)^{b} = {coeff} * s^{n}",
            "Ksp": ksp,
        }

    def _ksp_complex(self, args: Dict[str, Any]) -> Dict[str, Any]:
        ksp = args.get("Ksp")
        kf = args.get("Kf")
        if ksp is None or kf is None:
            return {
                "status": "error",
                "error": "Both Ksp and Kf are required for ksp_complex.",
            }
        args.get("stoich_cation") or 1
        args.get("stoich_anion") or 3

        k_overall = ksp * kf
        kw = 1e-14

        # Newton's method on charge balance equation
        h = (3.0 * ksp / k_overall) ** 0.25 if k_overall > 0 else 1e-7
        for _ in range(200):
            h2, h3, h4 = h * h, h * h * h, h * h * h * h
            f_val = 3.0 * ksp / h3 + kw / h - h - k_overall * h
            f_prime = -9.0 * ksp / h4 - kw / h2 - 1.0 - k_overall
            delta = f_val / f_prime
            h_new = h - delta
            if h_new <= 0:
                h = h / 2.0
                continue
            if abs(delta) < 1e-20 * h:
                h = h_new
                break
            h = h_new

        x = ksp / (h**3)  # free cation
        y = k_overall * h  # complex
        s = x + y

        return {
            "status": "success",
            "problem_type": "ksp_complex",
            "solubility_mol_per_L": s,
            "free_cation_conc": x,
            "complex_conc": y,
            "free_anion_conc": h,
            "K_overall": k_overall,
            "Ksp": ksp,
            "Kf": kf,
            "note": (
                f"Overall K = Ksp * Kf = {k_overall:.4e}. "
                f"Complex dominates: [complex]/[free cation] = {y / x:.2e}"
                if x > 0
                else "All dissolved as complex."
            ),
        }

    def _common_ion(self, args: Dict[str, Any]) -> Dict[str, Any]:
        ksp = args.get("Ksp")
        if ksp is None:
            return {"status": "error", "error": "Ksp is required."}
        a = args.get("stoich_cation") or 1
        b = args.get("stoich_anion") or 1
        c = args.get("common_ion_conc")
        if c is None:
            return {
                "status": "error",
                "error": "common_ion_conc is required for common_ion mode.",
            }

        def ksp_expr(s):
            return ((a * s) ** a) * ((b * s + c) ** b)

        s_max = (ksp / ((a**a) * (b**b))) ** (1.0 / (a + b))
        s_lo, s_hi = 0.0, s_max
        for _ in range(200):
            s_mid = (s_lo + s_hi) / 2.0
            if ksp_expr(s_mid) < ksp:
                s_lo = s_mid
            else:
                s_hi = s_mid
            if (s_hi - s_lo) < 1e-20:
                break
        s = (s_lo + s_hi) / 2.0
        s_approx = (ksp / ((a**a) * (c**b))) ** (1.0 / a)

        return {
            "status": "success",
            "problem_type": "common_ion",
            "solubility_mol_per_L": s,
            "solubility_approx_mol_per_L": s_approx,
            "cation_conc": a * s,
            "anion_conc": b * s + c,
            "common_ion_added": c,
            "Ksp": ksp,
        }

    # ── Tool 4: Enzyme kinetics ──

    def _michaelis_menten(self, args: Dict[str, Any]) -> Dict[str, Any]:
        substrate = args.get("substrate_concs")
        velocity = args.get("velocities")
        if not substrate or not velocity:
            return {
                "status": "error",
                "error": "substrate_concs and velocities are required.",
            }
        if len(substrate) != len(velocity):
            return {
                "status": "error",
                "error": "substrate_concs and velocities must have the same length.",
            }
        if len(substrate) < 3:
            return {"status": "error", "error": "Need at least 3 data points."}

        # Lineweaver-Burk
        inv_s = [1.0 / s for s in substrate]
        inv_v = [1.0 / v for v in velocity]
        slope, intercept, r2 = _linreg(inv_s, inv_v)

        lb_result = {}
        if intercept > 0 and slope > 0:
            lb_vmax = 1.0 / intercept
            lb_km = slope * lb_vmax
            lb_result = {
                "Vmax": round(lb_vmax, 6),
                "Km": round(lb_km, 6),
                "R2": round(r2, 6),
            }
        else:
            lb_result = {"note": "Non-physical parameters from Lineweaver-Burk."}

        # Nonlinear grid search
        best_sse = float("inf")
        best_km, best_vmax = substrate[len(substrate) // 2], max(velocity) * 1.2
        for vmax_mult in [x * 0.1 for x in range(5, 31)]:
            for km_mult in [x * 0.1 for x in range(1, 51)]:
                vm = max(velocity) * vmax_mult
                km = max(substrate) * km_mult * 0.1
                sse = sum(
                    (v - vm * s / (km + s)) ** 2 for s, v in zip(substrate, velocity)
                )
                if sse < best_sse:
                    best_sse = sse
                    best_km, best_vmax = km, vm

        for _ in range(5):
            step_v = best_vmax * 0.05
            step_k = best_km * 0.05
            improved = False
            for dv in [-step_v, 0, step_v]:
                for dk in [-step_k, 0, step_k]:
                    vm = best_vmax + dv
                    km = best_km + dk
                    if vm <= 0 or km <= 0:
                        continue
                    sse = sum(
                        (v - vm * s / (km + s)) ** 2
                        for s, v in zip(substrate, velocity)
                    )
                    if sse < best_sse:
                        best_sse = sse
                        best_km, best_vmax = km, vm
                        improved = True
            if not improved:
                break

        v_mean = sum(velocity) / len(velocity)
        ss_tot = sum((v - v_mean) ** 2 for v in velocity)
        nl_r2 = 1.0 - best_sse / ss_tot if ss_tot > 0 else 0.0

        predicted = [round(best_vmax * s / (best_km + s), 6) for s in substrate]
        residuals = [round(v - p, 6) for v, p in zip(velocity, predicted)]

        return {
            "status": "success",
            "calculation_type": "michaelis_menten",
            "lineweaver_burk": lb_result,
            "nonlinear_fit": {
                "Vmax": round(best_vmax, 6),
                "Km": round(best_km, 6),
                "R2": round(nl_r2, 6),
                "SSE": round(best_sse, 6),
            },
            "Vmax": round(best_vmax, 6),
            "Km": round(best_km, 6),
            "catalytic_efficiency": round(best_vmax / best_km, 6),
            "predicted_velocities": predicted,
            "residuals": residuals,
        }

    def _hill(self, args: Dict[str, Any]) -> Dict[str, Any]:
        substrate = args.get("substrate_concs")
        velocity = args.get("velocities")
        if not substrate or not velocity:
            return {
                "status": "error",
                "error": "substrate_concs and velocities are required.",
            }
        if len(substrate) != len(velocity):
            return {
                "status": "error",
                "error": "substrate_concs and velocities must have the same length.",
            }
        if len(substrate) < 3:
            return {"status": "error", "error": "Need at least 3 data points."}

        vmax_est = max(velocity) * 1.1

        log_s, log_y = [], []
        for s, v in zip(substrate, velocity):
            if 0.1 * vmax_est < v < 0.9 * vmax_est:
                y = v / (vmax_est - v)
                if y > 0:
                    log_s.append(math.log10(s))
                    log_y.append(math.log10(y))

        if len(log_s) < 2:
            vmax_est = max(velocity) * 1.3
            for s, v in zip(substrate, velocity):
                if 0.05 * vmax_est < v < 0.95 * vmax_est:
                    y = v / (vmax_est - v)
                    if y > 0:
                        log_s.append(math.log10(s))
                        log_y.append(math.log10(y))

        if len(log_s) < 2:
            return {
                "status": "error",
                "error": "Insufficient data in the 10-90% saturation range for Hill analysis.",
            }

        slope, intercept, r2 = _linreg(log_s, log_y)
        nH = slope
        k05 = 10 ** (-intercept / nH) if abs(nH) > 1e-10 else float("inf")

        if nH > 1.05:
            interp = f"nH = {nH:.2f} > 1: POSITIVE cooperativity"
        elif nH < 0.95:
            interp = f"nH = {nH:.2f} < 1: NEGATIVE cooperativity"
        else:
            interp = f"nH = {nH:.2f} ~ 1: NO cooperativity (independent sites)"

        predicted = [
            round(vmax_est * (s**nH) / (k05**nH + s**nH), 6) for s in substrate
        ]

        return {
            "status": "success",
            "calculation_type": "hill",
            "hill_coefficient": round(nH, 4),
            "K05": round(k05, 6),
            "Vmax_estimated": round(vmax_est, 6),
            "R2_hill_plot": round(r2, 6),
            "interpretation": interp,
            "data_points_used": len(log_s),
            "predicted_velocities": predicted,
        }

    def _inhibition(self, args: Dict[str, Any]) -> Dict[str, Any]:
        substrate = args.get("substrate_concs")
        v_no_inh = args.get("velocities_no_inhibitor")
        v_inh = args.get("velocities_with_inhibitor")
        inh_conc = args.get("inhibitor_conc")
        inh_type = (args.get("inhibition_type") or "competitive").lower().strip()

        if not substrate or not v_no_inh or not v_inh:
            return {
                "status": "error",
                "error": "substrate_concs, velocities_no_inhibitor, and velocities_with_inhibitor required.",
            }
        if inh_conc is None:
            return {"status": "error", "error": "inhibitor_conc is required."}
        n = len(substrate)
        if len(v_no_inh) != n or len(v_inh) != n:
            return {"status": "error", "error": "All arrays must have the same length."}
        if n < 3:
            return {"status": "error", "error": "Need at least 3 data points."}

        inv_s = [1.0 / s for s in substrate]
        inv_v0 = [1.0 / v for v in v_no_inh]
        slope0, intercept0, r2_0 = _linreg(inv_s, inv_v0)

        if intercept0 <= 0 or slope0 <= 0:
            return {
                "status": "error",
                "error": "Uninhibited data does not give valid Km/Vmax.",
            }

        vmax = 1.0 / intercept0
        km = slope0 * vmax

        inv_vi = [1.0 / v for v in v_inh]
        slope_i, intercept_i, r2_i = _linreg(inv_s, inv_vi)

        if intercept_i <= 0 or slope_i <= 0:
            return {
                "status": "error",
                "error": "Inhibited data does not give valid apparent parameters.",
            }

        vmax_app = 1.0 / intercept_i
        km_app = slope_i * vmax_app

        ki = None
        if inh_type == "competitive":
            ratio = km_app / km
            ki = inh_conc / (ratio - 1.0) if ratio > 1.0 else None
        elif inh_type == "uncompetitive":
            ratio = vmax / vmax_app
            ki = inh_conc / (ratio - 1.0) if ratio > 1.0 else None
        elif inh_type in ("noncompetitive", "non-competitive"):
            ratio = vmax / vmax_app
            ki = inh_conc / (ratio - 1.0) if ratio > 1.0 else None
        else:
            return {
                "status": "error",
                "error": f"Unknown inhibition type: {inh_type}. Use competitive, uncompetitive, or noncompetitive.",
            }

        result: Dict[str, Any] = {
            "status": "success",
            "calculation_type": "inhibition",
            "inhibition_type": inh_type,
            "Vmax": round(vmax, 6),
            "Km": round(km, 6),
            "Vmax_apparent": round(vmax_app, 6),
            "Km_apparent": round(km_app, 6),
            "inhibitor_conc": inh_conc,
        }
        if ki is not None:
            result["Ki"] = round(ki, 6)
        else:
            result["Ki_note"] = (
                "Ki could not be determined. Data inconsistent with the specified inhibition model."
            )

        return result

    # ── Tool 5: Statistical tests ──

    def _chi_square(self, args: Dict[str, Any]) -> Dict[str, Any]:
        observed = args.get("observed")
        expected = args.get("expected")
        if not observed or not expected:
            return {"status": "error", "error": "observed and expected are required."}
        if len(observed) != len(expected):
            return {
                "status": "error",
                "error": "observed and expected must have the same length.",
            }
        if len(observed) < 2:
            return {"status": "error", "error": "Need at least 2 categories."}

        n_obs = sum(observed)
        n_exp = sum(expected)
        if n_obs <= 0 or n_exp <= 0:
            return {"status": "error", "error": "Sums must be > 0."}

        scale = n_obs / n_exp
        exp_scaled = [e * scale for e in expected]
        chi2 = sum((o - e) ** 2 / e for o, e in zip(observed, exp_scaled))
        df = len(observed) - 1
        p = _chi_square_p_value(chi2, df)
        contributions = [
            round((o - e) ** 2 / e, 6) for o, e in zip(observed, exp_scaled)
        ]

        warning = None
        if min(exp_scaled) < 5:
            warning = f"Minimum expected count {min(exp_scaled):.2f} < 5. Chi-square approximation may be unreliable."

        return {
            "status": "success",
            "test_type": "chi_square",
            "chi2": round(chi2, 6),
            "df": df,
            "p_value": round(p, 8),
            "significant_at_005": p < 0.05,
            "contributions": contributions,
            "expected_scaled": [round(e, 4) for e in exp_scaled],
            "warning": warning,
        }

    def _fisher_exact(self, args: Dict[str, Any]) -> Dict[str, Any]:
        cell_a = args.get("a")
        cell_b = args.get("b")
        cell_c = args.get("c")
        cell_d = args.get("d")
        alternative = args.get("alternative") or "two-sided"

        if any(v is None for v in [cell_a, cell_b, cell_c, cell_d]):
            return {"status": "error", "error": "a, b, c, and d are all required."}
        if any(v < 0 for v in [cell_a, cell_b, cell_c, cell_d]):
            return {"status": "error", "error": "All cell counts must be >= 0."}

        n1 = cell_a + cell_b
        n2 = cell_c + cell_d
        n = cell_a + cell_c
        N = cell_a + cell_b + cell_c + cell_d
        if N == 0:
            return {"status": "error", "error": "All counts are zero."}

        if cell_b * cell_c == 0:
            OR = float("inf") if cell_a * cell_d != 0 else float("nan")
        else:
            OR = (cell_a * cell_d) / (cell_b * cell_c)

        k_min = max(0, n - n2)
        k_max = min(n1, n)
        all_probs = {
            k: _hypergeometric_pmf(k, n1, n2, n) for k in range(k_min, k_max + 1)
        }
        p_obs = all_probs.get(cell_a, 0.0)

        if alternative == "two-sided":
            p_value = sum(p for p in all_probs.values() if p <= p_obs + 1e-10)
        elif alternative == "less":
            p_value = sum(p for k, p in all_probs.items() if k <= cell_a)
        elif alternative == "greater":
            p_value = sum(p for k, p in all_probs.items() if k >= cell_a)
        else:
            return {"status": "error", "error": f"Invalid alternative: {alternative}"}

        p_value = min(p_value, 1.0)

        return {
            "status": "success",
            "test_type": "fisher_exact",
            "odds_ratio": round(OR, 6)
            if not (math.isinf(OR) or math.isnan(OR))
            else str(OR),
            "p_value": round(p_value, 8),
            "alternative": alternative,
            "significant_at_005": p_value < 0.05,
            "table": {"a": cell_a, "b": cell_b, "c": cell_c, "d": cell_d},
            "marginals": {
                "row1": n1,
                "row2": n2,
                "col1": n,
                "col2": cell_b + cell_d,
                "N": N,
            },
        }

    def _linear_regression(self, args: Dict[str, Any]) -> Dict[str, Any]:
        x = args.get("data_x")
        y = args.get("data_y")
        if not x or not y:
            return {"status": "error", "error": "data_x and data_y are required."}
        n = len(x)
        if n != len(y):
            return {
                "status": "error",
                "error": "data_x and data_y must have the same length.",
            }
        if n < 3:
            return {"status": "error", "error": "Need at least 3 data points."}

        x_mean = sum(x) / n
        y_mean = sum(y) / n
        Sxx = sum((xi - x_mean) ** 2 for xi in x)
        Sxy = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y))
        Syy = sum((yi - y_mean) ** 2 for yi in y)

        if Sxx == 0:
            return {"status": "error", "error": "All x values are identical."}

        b1 = Sxy / Sxx
        b0 = y_mean - b1 * x_mean
        y_pred = [b0 + b1 * xi for xi in x]
        residuals = [yi - yp for yi, yp in zip(y, y_pred)]
        SSR = sum(r**2 for r in residuals)
        SST = Syy
        R2 = 1.0 - SSR / SST if SST > 0 else float("nan")
        R2_adj = (
            1.0 - (SSR / (n - 2)) / (SST / (n - 1))
            if n > 2 and SST > 0
            else float("nan")
        )

        s2 = SSR / (n - 2)
        se_b1 = math.sqrt(s2 / Sxx)
        t_b1 = b1 / se_b1 if se_b1 > 0 else float("nan")
        p_b1 = _t_pvalue(t_b1, n - 2)
        r = Sxy / math.sqrt(Sxx * Syy) if Sxx > 0 and Syy > 0 else float("nan")

        return {
            "status": "success",
            "test_type": "linear_regression",
            "n": n,
            "slope": round(b1, 6),
            "intercept": round(b0, 6),
            "se_slope": round(se_b1, 6),
            "t_slope": round(t_b1, 6),
            "p_slope": round(p_b1, 8),
            "R2": round(R2, 6),
            "R2_adj": round(R2_adj, 6),
            "pearson_r": round(r, 6),
            "equation": f"y = {b0:.4f} + {b1:.4f} * x",
            "predicted": [round(yp, 6) for yp in y_pred],
            "residuals": [round(ri, 6) for ri in residuals],
        }

    def _t_test(self, args: Dict[str, Any]) -> Dict[str, Any]:
        x = args.get("data_x")
        y = args.get("data_y")
        if not x or not y:
            return {"status": "error", "error": "data_x and data_y are required."}
        n1, n2 = len(x), len(y)
        if n1 < 2 or n2 < 2:
            return {
                "status": "error",
                "error": "Each group needs at least 2 observations.",
            }

        m1 = sum(x) / n1
        m2 = sum(y) / n2
        s1_sq = sum((xi - m1) ** 2 for xi in x) / (n1 - 1)
        s2_sq = sum((yi - m2) ** 2 for yi in y) / (n2 - 1)

        se = math.sqrt(s1_sq / n1 + s2_sq / n2)
        if se == 0:
            return {"status": "error", "error": "Both groups have zero variance."}

        t_stat = (m1 - m2) / se

        # Welch-Satterthwaite degrees of freedom
        num = (s1_sq / n1 + s2_sq / n2) ** 2
        denom = (s1_sq / n1) ** 2 / (n1 - 1) + (s2_sq / n2) ** 2 / (n2 - 1)
        df = num / denom if denom > 0 else min(n1, n2) - 1

        p_val = _t_pvalue(t_stat, int(round(df)))

        return {
            "status": "success",
            "test_type": "t_test",
            "mean_x": round(m1, 6),
            "mean_y": round(m2, 6),
            "mean_difference": round(m1 - m2, 6),
            "t_statistic": round(t_stat, 6),
            "degrees_of_freedom": round(df, 2),
            "p_value": round(p_val, 8),
            "significant_at_005": p_val < 0.05,
            "variance_x": round(s1_sq, 6),
            "variance_y": round(s2_sq, 6),
        }
