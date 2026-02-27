# nca_tool.py
"""
Non-Compartmental Analysis (NCA) Tool for Pharmacokinetics

Implements standard NCA methods per FDA/EMA regulatory guidelines:
- Full NCA parameter calculation from time-concentration data
  (Cmax, Tmax, AUC0-t, AUC0-inf, t½, CL, Vd)
- One-compartment IV bolus model fitting: C(t) = C0 * exp(-k_el * t)
- Oral bioavailability (F) calculation

No external API calls. Uses numpy/scipy for computation.

References:
- FDA Guidance for Industry: Pharmacokinetics in Patients with Impaired Renal Function
- Gabrielsson & Weiner, Pharmacokinetic and Pharmacodynamic Data Analysis (2016)
- Rowland & Tozer, Clinical Pharmacokinetics and Pharmacodynamics (2011)
"""

from typing import Dict, Any

from .base_tool import BaseTool
from .tool_registry import register_tool

try:
    import numpy as np

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    from scipy.optimize import curve_fit
    from scipy.stats import linregress

    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

# Unit conversion tables for automatic PK unit standardization
_MASS_TO_NG: dict = {
    "pg": 1e-3,
    "ng": 1.0,
    "μg": 1e3,
    "ug": 1e3,
    "mcg": 1e3,
    "mg": 1e6,
    "g": 1e9,
    "kg": 1e12,
}
_CONC_TO_NG_PER_ML: dict = {
    "pg/ml": 1e-3,
    "pg/l": 1e-6,
    "ng/ml": 1.0,
    "ng/l": 1e-3,
    "μg/ml": 1e3,
    "ug/ml": 1e3,
    "mcg/ml": 1e3,
    "μg/l": 1.0,
    "ug/l": 1.0,
    "mg/ml": 1e6,
    "mg/l": 1e3,
    "g/ml": 1e9,
    "g/l": 1e6,
}


@register_tool("NCATool")
class NCATool(BaseTool):
    """
    Non-Compartmental Analysis (NCA) for pharmacokinetics.

    Endpoints:
    - compute_parameters: Full NCA from time-concentration data
    - fit_one_compartment: 1-compartment IV bolus model fitting
    - calculate_bioavailability: Oral bioavailability F calculation
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "compute_parameters")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not HAS_NUMPY:
            return {
                "status": "error",
                "error": "numpy is required for NCA calculations. Install with: pip install numpy",
            }

        try:
            if self.endpoint == "compute_parameters":
                return self._compute_parameters(arguments)
            elif self.endpoint == "fit_one_compartment":
                return self._fit_one_compartment(arguments)
            elif self.endpoint == "calculate_bioavailability":
                return self._calculate_bioavailability(arguments)
            else:
                return {
                    "status": "error",
                    "error": f"Unknown endpoint: {self.endpoint}",
                }
        except Exception as e:
            return {"status": "error", "error": f"NCA calculation error: {str(e)}"}

    def _auc_trapezoid(self, times: "np.ndarray", concs: "np.ndarray") -> float:
        """
        Linear-log trapezoidal AUC calculation.

        Uses logarithmic trapezoid for declining phases (more accurate),
        linear trapezoid for ascending phases and zero concentrations.
        """
        auc = 0.0
        for i in range(len(times) - 1):
            dt = float(times[i + 1] - times[i])
            c1, c2 = float(concs[i]), float(concs[i + 1])
            if c1 <= 0 or c2 <= 0:
                # Linear trapezoid when values near zero
                auc += dt * (c1 + c2) / 2.0
            elif c2 < c1:
                # Logarithmic trapezoid (declining phase)
                auc += dt * (c1 - c2) / np.log(c1 / c2)
            else:
                # Linear trapezoid (ascending phase)
                auc += dt * (c1 + c2) / 2.0
        return auc

    def _estimate_terminal_slope(
        self,
        times: "np.ndarray",
        concs: "np.ndarray",
        n_points: int = 3,
        tmax: float = None,
    ):
        """
        Estimate terminal elimination rate constant (λz) from log-linear regression.

        Per FDA NCA guidance (2003) and Rowland & Tozer (2011), λz should be estimated
        from all time points in the log-linear terminal phase, which begins after Tmax.
        When tmax is provided, all post-Tmax positive-concentration points are used.
        Falls back to the last n_points if fewer than 2 post-Tmax points are available.

        Returns: (lambda_z, r_squared, intercept) or (None, None, None) on failure.
        """
        if not HAS_SCIPY:
            return None, None, None

        # Use positive concentrations only
        valid = concs > 0
        t_valid = times[valid]
        c_valid = concs[valid]

        if len(t_valid) < 2:
            return None, None, None

        # Select terminal phase points
        # FDA NCA guidance requires ≥3 points for reliable λz: a 2-point regression
        # is a perfect fit by construction (R²=1 always), giving no quality signal.
        if tmax is not None:
            post_tmax = t_valid > tmax
            if np.sum(post_tmax) >= 3:
                # FDA NCA: use all post-Tmax points for λz estimation
                t_term = t_valid[post_tmax]
                c_term = c_valid[post_tmax]
            else:
                # Insufficient post-Tmax points: cannot reliably estimate λz.
                # Including Tmax or pre-Tmax points in the regression would
                # violate FDA NCA guidance (terminal phase begins after Tmax).
                # The caller will emit a terminal_phase_warning.
                return None, None, None
        else:
            n_use = min(n_points, len(t_valid))
            t_term = t_valid[-n_use:]
            c_term = c_valid[-n_use:]

        # log-linear fit: ln(C) = intercept - λz * t
        slope, intercept, r_value, _, _ = linregress(t_term, np.log(c_term))

        if slope >= 0:
            return None, None, None  # Must be negative (declining)

        lambda_z = -slope  # λz positive
        r_squared = r_value**2

        return float(lambda_z), float(r_squared), float(intercept)

    def _try_pk_unit_conversion(self, dose_val: float, dose_unit: str, conc_unit: str):
        """
        Try to convert dose and concentration to standard base units (ng, ng/mL).

        Returns (dose_ng, conc_factor, True) on success, or (None, None, False) for
        unknown units.  conc_factor multiplies raw concentration to obtain ng/mL.
        """
        mass_factor = _MASS_TO_NG.get(dose_unit.lower().strip())
        conc_factor = _CONC_TO_NG_PER_ML.get(conc_unit.lower().strip())
        if mass_factor is not None and conc_factor is not None:
            return dose_val * mass_factor, conc_factor, True
        return None, None, False

    def _compute_parameters(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Full NCA computation from time-concentration data."""
        times = arguments.get("times", [])
        concentrations = arguments.get("concentrations", [])
        dose = arguments.get("dose")
        route = arguments.get("route", "iv")
        dose_unit = arguments.get("dose_unit", "mg")
        conc_unit = arguments.get("conc_unit", "ng/mL")
        time_unit = arguments.get("time_unit", "h")

        if not times or not concentrations:
            return {
                "status": "error",
                "error": "times and concentrations are required. Provide paired lists of time points and measured concentrations.",
            }
        if len(times) != len(concentrations):
            return {
                "status": "error",
                "error": "times and concentrations must have the same length",
            }
        if len(times) < 3:
            return {
                "status": "error",
                "error": "At least 3 time-concentration points are required for NCA",
            }

        try:
            t = np.array([float(x) for x in times])
            c = np.array([float(x) for x in concentrations])
        except (ValueError, TypeError) as e:
            return {"status": "error", "error": f"Invalid numeric values: {e}"}

        # NaN/inf must be rejected before any comparison (np.any(c < 0) returns False
        # for NaN, silently bypassing the negative-value guard).
        if np.any(~np.isfinite(c)):
            return {
                "status": "error",
                "error": (
                    "Concentrations contain non-finite values (NaN or inf). "
                    "All concentration values must be finite real numbers. "
                    "Replace NaN/inf with 0 (BLQ) or remove the affected time points."
                ),
            }

        if np.any(c < 0):
            return {
                "status": "error",
                "error": (
                    "All concentrations must be non-negative. Negative values likely "
                    "represent below-LOQ (BLQ) measurements. Per FDA/EMA NCA guidance, "
                    "replace BLQ values with 0 before submitting."
                ),
            }

        # Sort by time
        sort_idx = np.argsort(t)
        t = t[sort_idx]
        c = c[sort_idx]

        # Basic parameters
        cmax = float(np.max(c))
        tmax = float(t[np.argmax(c)])
        pos_mask = c > 0
        clast = float(c[pos_mask][-1]) if any(pos_mask) else 0.0
        tlast = float(t[pos_mask][-1]) if any(pos_mask) else 0.0

        # Detect mid-profile zeros: a zero concentration that appears between two
        # positive values is biologically implausible and may indicate assay failure,
        # sample swap, or re-absorption.  Collect positions for a warning.
        mid_profile_zero_times = []
        first_pos = int(np.argmax(pos_mask)) if any(pos_mask) else len(c)
        last_pos = len(c) - 1 - int(np.argmax(pos_mask[::-1])) if any(pos_mask) else -1
        for idx in range(first_pos + 1, last_pos):
            if c[idx] == 0.0:
                mid_profile_zero_times.append(float(t[idx]))

        # AUC0-t (linear-log trapezoidal).
        # FDA NCA convention: AUC0-t is integrated only up to Tlast, the time of
        # the last *positive* (measurable) concentration.  Trailing zeros beyond
        # Tlast represent BLQ samples and must not inflate the integral.
        # Pre-dose time points (t < 0) must also be excluded: including them inflates
        # the area by integrating over negative-time intervals that are not part of
        # the post-administration pharmacokinetic profile.
        if any(pos_mask):
            last_pos_idx = int(np.where(pos_mask)[0][-1])
            first_nonneg_idx = int(np.argmax(t >= 0)) if np.any(t >= 0) else 0
            t_auc = t[first_nonneg_idx : last_pos_idx + 1]
            c_auc = c[first_nonneg_idx : last_pos_idx + 1]
            pre_dose_times = [float(x) for x in t[:first_nonneg_idx]]
        else:
            t_auc = t
            c_auc = c
            pre_dose_times = []
        auc0t = self._auc_trapezoid(t_auc, c_auc)

        # Terminal phase parameters — use all post-Tmax points per FDA NCA guidance
        lambda_z, r_sq_terminal, _ = self._estimate_terminal_slope(t, c, tmax=tmax)

        result = {
            "Cmax": round(cmax, 4),
            "Tmax": round(tmax, 4),
            "Clast": round(clast, 4),
            "Tlast": round(tlast, 4),
            f"AUC0-{tlast:.1f}": round(auc0t, 4),
            "AUC0_last": round(auc0t, 4),  # stable alias for programmatic access
            "units": {
                "Cmax": conc_unit,
                "Tmax": time_unit,
                "AUC": f"{conc_unit}·{time_unit}",
            },
        }

        # Warn when pre-dose (t < 0) time points were excluded from AUC integration.
        if pre_dose_times:
            result["pre_dose_time_warning"] = (
                f"Pre-dose time points (t < 0) at t={pre_dose_times} were excluded "
                "from AUC integration. AUC0-t is computed from t=0 per FDA/EMA NCA "
                "guidance. Pre-dose samples are retained for visual inspection only."
            )

        # Check monotonicity of post-Tmax concentrations.
        # Non-monotonic profiles (rising concentrations after Tmax) indicate
        # re-absorption, enterohepatic circulation, or assay issues — making
        # terminal slope estimation unreliable.
        valid_mask = c > 0
        t_valid_all = t[valid_mask]
        c_valid_all = c[valid_mask]
        post_tmax_mask = t_valid_all > tmax
        if np.sum(post_tmax_mask) >= 3:
            c_post = c_valid_all[post_tmax_mask]
            if np.any(np.diff(c_post) > 0):
                result["non_monotonic_terminal_warning"] = (
                    "Post-Tmax concentrations are not monotonically decreasing. "
                    "This may indicate re-absorption, enterohepatic circulation, a secondary "
                    "Cmax, or assay variability. Terminal slope (lambda_z) may be unreliable."
                )

        if lambda_z is not None:
            t_half = np.log(2) / lambda_z
            # AUC0-inf = AUC0-t + Clast/λz
            auc0inf = auc0t + clast / lambda_z
            extrap_pct = float((clast / lambda_z) / auc0inf * 100)
            # Preserve full precision for lambda_z: round(1e-9, 6) = 0.0 which is wrong.
            result["lambda_z"] = round(float(lambda_z), 9)
            result["t_half"] = round(float(t_half), 4)
            result["r_squared_terminal_fit"] = round(float(r_sq_terminal), 4)
            result["AUC0-inf"] = round(float(auc0inf), 4)
            result["AUC_extrapolation_pct"] = round(extrap_pct, 1)
            if extrap_pct > 20.0:
                result["AUC_extrapolation_warning"] = (
                    f"AUC extrapolation is {extrap_pct:.1f}% (>20%). "
                    "AUC0-inf may be unreliable. Add more late time points to "
                    "better characterize the terminal elimination phase "
                    "(FDA/EMA guideline: extrapolation should be <20%)."
                )

            if dose is not None:
                try:
                    dose_val = float(dose)
                    if dose_val <= 0:
                        return {
                            "status": "error",
                            "error": (
                                f"dose ({dose_val}) must be positive (> 0). "
                                "Negative or zero dose is not physically meaningful. "
                                "CL and Vd cannot be computed without a positive dose."
                            ),
                        }
                    dose_ng, conc_factor, converted = self._try_pk_unit_conversion(
                        dose_val, dose_unit, conc_unit
                    )
                    if converted:
                        # AUC in (ng/mL)·time_unit after applying conc_factor
                        auc_ng_ml = auc0inf * conc_factor
                        cl_ml = dose_ng / auc_ng_ml  # mL/time_unit
                        cl_l = cl_ml / 1000.0  # L/time_unit
                        result["clearance_CL"] = round(float(cl_l), 6)
                        result["clearance_CL_unit"] = f"L/{time_unit}"
                        if route == "iv":
                            vd_l = cl_l / lambda_z  # L
                            result["volume_distribution_Vd"] = round(float(vd_l), 4)
                            result["Vd_unit"] = "L"
                            result["MRT_iv"] = round(float(1.0 / lambda_z), 4)
                    else:
                        cl = dose_val / auc0inf
                        result["clearance_CL"] = round(float(cl), 6)
                        result["clearance_CL_unit"] = (
                            f"{dose_unit}/({conc_unit}·{time_unit})"
                        )
                        result["pk_unit_note"] = (
                            f"Automatic unit conversion not available for "
                            f"dose_unit='{dose_unit}' / conc_unit='{conc_unit}'. "
                            "CL and Vd are in raw ratio units; convert manually."
                        )
                        if route == "iv":
                            vd = cl / lambda_z
                            result["volume_distribution_Vd"] = round(float(vd), 4)
                            result["Vd_unit"] = f"{dose_unit}/{conc_unit}"
                            result["MRT_iv"] = round(float(1.0 / lambda_z), 4)
                except (ValueError, TypeError):
                    pass
        else:
            result["terminal_phase_warning"] = (
                "Could not estimate terminal slope (λz). "
                "Add more time points in the terminal elimination phase."
            )

        if mid_profile_zero_times:
            result["mid_profile_zero_warning"] = (
                f"Zero concentration detected at t={mid_profile_zero_times} between "
                "positive values. This is biologically implausible and may indicate "
                "assay failure, sample swap, or re-absorption. "
                "AUC calculation proceeds via linear trapezoid at those intervals "
                "but the result may be unreliable."
            )

        result["method"] = "Linear-log trapezoidal NCA"
        result["note"] = (
            "AUC uses linear trapezoid for ascending phases and log-trapezoid "
            "for declining phases (FDA/EMA recommended method). "
            "Terminal t½ estimated from log-linear regression of last 3+ positive concentrations."
        )

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "Local NCA computation (numpy/scipy)",
                "n_timepoints": len(t),
                "route_of_administration": route,
                "reference": "FDA NCA Guidance; Gabrielsson & Weiner (2016)",
            },
        }

    def _fit_one_compartment(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Fit 1-compartment IV bolus model: C(t) = C0 * exp(-k_el * t)."""
        if not HAS_SCIPY:
            return {
                "status": "error",
                "error": "scipy is required for model fitting. Install with: pip install scipy",
            }

        times = arguments.get("times", [])
        concentrations = arguments.get("concentrations", [])
        dose = arguments.get("dose")
        dose_unit = arguments.get("dose_unit", "mg")
        conc_unit = arguments.get("conc_unit", "ng/mL")
        time_unit = arguments.get("time_unit", "h")

        if not times or not concentrations:
            return {"status": "error", "error": "times and concentrations are required"}
        if len(times) != len(concentrations):
            return {
                "status": "error",
                "error": "times and concentrations must have the same length",
            }

        try:
            t = np.array([float(x) for x in times])
            c = np.array([float(x) for x in concentrations])
        except (ValueError, TypeError) as e:
            return {"status": "error", "error": f"Invalid numeric values: {e}"}

        # Use positive concentrations only
        valid = c > 0
        if sum(valid) < 3:
            return {
                "status": "error",
                "error": "At least 3 positive concentration values required for model fitting",
            }

        t_fit = t[valid]
        c_fit = c[valid]

        def one_compartment(t_arr, c0, k_el):
            return c0 * np.exp(-k_el * t_arr)

        try:
            c0_init = float(c_fit[0]) if c_fit[0] > 0 else float(np.max(c_fit))
            k_init = np.log(2) / (float(t_fit[-1]) / 2 + 1e-9)

            popt, pcov = curve_fit(
                one_compartment,
                t_fit,
                c_fit,
                p0=[c0_init, k_init],
                bounds=([0.0, 1e-9], [np.inf, np.inf]),
                maxfev=10000,
            )
            c0_fit, k_el_fit = popt
            perr = np.sqrt(np.diag(pcov))
        except Exception as e:
            return {
                "status": "error",
                "error": f"Model fitting failed: {str(e)}. Ensure data follows mono-exponential decline.",
            }

        t_half = np.log(2) / k_el_fit

        # R² on fitted points
        c_pred = one_compartment(t_fit, c0_fit, k_el_fit)
        ss_res = float(np.sum((c_fit - c_pred) ** 2))
        ss_tot = float(np.sum((c_fit - np.mean(c_fit)) ** 2))
        r_squared = float(1.0 - ss_res / ss_tot) if ss_tot > 0 else 0.0

        if r_squared >= 0.95:
            gof = "Good (R²≥0.95)"
        elif r_squared >= 0.85:
            gof = "Moderate (0.85≤R²<0.95)"
        else:
            gof = "Poor (R²<0.85) — consider multi-compartment model"

        # Preserve full precision for k_el: round(1e-9, 6) = 0.0, which is wrong
        # for drugs near the lower optimization bound (1e-9 h⁻¹ ≡ t½ ≈ 693M h).
        k_el_val = float(k_el_fit)
        # SE of k_el needs same precision to avoid reporting 0.0.
        k_el_se_val = float(perr[1])

        result = {
            "model": "1-compartment IV bolus",
            "equation": "C(t) = C0 × exp(-k_el × t)",
            "C0_initial_concentration": round(float(c0_fit), 4),
            "k_el_elimination_rate": k_el_val,
            "t_half": round(float(t_half), 4),
            "r_squared": round(r_squared, 4),
            "goodness_of_fit": gof,
            "standard_errors": {
                "C0": round(float(perr[0]), 4),
                "k_el": k_el_se_val,
            },
            "units": {
                "C0": conc_unit,
                "k_el": f"1/{time_unit}",
                "t_half": time_unit,
            },
        }

        # Warn when k_el is at or near the optimization lower bound (1e-9).
        # At the bound, the optimizer could not find a smaller value — the half-life
        # estimate (ln2/k_el) may be astronomically large and unreliable.
        if k_el_val < 1e-8:
            result["k_el_bound_warning"] = (
                f"k_el ({k_el_val:.2e} 1/{time_unit}) is at or near the optimization "
                "lower bound (1e-9). This may indicate an extremely long half-life drug "
                "or that the data do not support reliable estimation of the elimination "
                f"rate constant. Corresponding t½ = {float(t_half):.4g} {time_unit} "
                "should be interpreted with great caution."
            )

        if dose is not None:
            try:
                dose_val = float(dose)
                auc0inf = c0_fit / k_el_fit
                dose_ng, conc_factor, converted = self._try_pk_unit_conversion(
                    dose_val, dose_unit, conc_unit
                )
                if converted:
                    c0_ng_per_ml = c0_fit * conc_factor
                    vd_ml = dose_ng / c0_ng_per_ml  # mL
                    vd_l = vd_ml / 1000.0  # L
                    cl_l = k_el_fit * vd_l  # L/time_unit
                    result["volume_distribution_Vd"] = round(float(vd_l), 4)
                    result["Vd_unit"] = "L"
                    result["clearance_CL"] = round(float(cl_l), 6)
                    result["CL_unit"] = f"L/{time_unit}"
                else:
                    vd_raw = dose_val / c0_fit
                    cl_raw = k_el_fit * vd_raw
                    result["volume_distribution_Vd"] = round(float(vd_raw), 4)
                    result["Vd_unit"] = f"{dose_unit}/{conc_unit}"
                    result["clearance_CL"] = round(float(cl_raw), 6)
                    result["CL_unit"] = f"{dose_unit}/({conc_unit}·{time_unit})"
                    result["pk_unit_note"] = (
                        f"Automatic unit conversion not available for "
                        f"dose_unit='{dose_unit}' / conc_unit='{conc_unit}'. "
                        "Vd and CL are in raw ratio units; convert manually."
                    )
                result["AUC0_inf_model"] = round(float(auc0inf), 4)
                result["AUC_unit"] = f"{conc_unit}·{time_unit}"
            except (ValueError, TypeError):
                pass

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "Local 1-compartment model fit (scipy.optimize.curve_fit)",
                "n_timepoints_fitted": int(sum(valid)),
            },
        }

    def _calculate_bioavailability(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate oral bioavailability F from IV and PO AUC and dose."""
        auc_po = arguments.get("auc_po")
        dose_po = arguments.get("dose_po")
        auc_iv = arguments.get("auc_iv")
        dose_iv = arguments.get("dose_iv")

        if auc_po is None or dose_po is None:
            return {
                "status": "error",
                "error": "auc_po and dose_po are required (PO arm AUC and dose)",
            }
        if auc_iv is None or dose_iv is None:
            return {
                "status": "error",
                "error": "auc_iv and dose_iv are required (IV arm AUC and dose)",
            }

        try:
            auc_po = float(auc_po)
            dose_po = float(dose_po)
            auc_iv = float(auc_iv)
            dose_iv = float(dose_iv)
        except (ValueError, TypeError) as e:
            return {"status": "error", "error": f"Invalid numeric values: {e}"}

        if auc_iv <= 0 or dose_iv <= 0 or dose_po <= 0:
            return {
                "status": "error",
                "error": "AUC_IV, dose_IV, and dose_PO must all be positive numbers",
            }

        # F = (AUC_PO × Dose_IV) / (AUC_IV × Dose_PO)
        f = (auc_po * dose_iv) / (auc_iv * dose_po)
        f_pct = f * 100.0

        auc_po_norm = auc_po / dose_po
        auc_iv_norm = auc_iv / dose_iv

        if f_pct >= 80.0:
            category = "High (≥80%)"
            note = "Excellent oral bioavailability. Suitable for oral dosing."
        elif f_pct >= 30.0:
            category = "Moderate (30–80%)"
            note = "Acceptable oral bioavailability for most indications."
        elif f_pct >= 10.0:
            category = "Low (10–30%)"
            note = "Poor oral absorption. Consider prodrug strategy or formulation optimization."
        else:
            category = "Very low (<10%)"
            note = "Insufficient oral bioavailability. Likely requires IV/SC/inhaled route."

        return {
            "status": "success",
            "data": {
                "bioavailability_F": round(float(f), 4),
                "bioavailability_pct": round(float(f_pct), 2),
                "category": category,
                "clinical_note": note,
                "formula": "F = (AUC_PO × Dose_IV) / (AUC_IV × Dose_PO)",
                "inputs": {
                    "AUC_PO": auc_po,
                    "Dose_PO": dose_po,
                    "AUC_IV": auc_iv,
                    "Dose_IV": dose_iv,
                    "AUC_PO_dose_normalized": round(float(auc_po_norm), 4),
                    "AUC_IV_dose_normalized": round(float(auc_iv_norm), 4),
                },
                "general_note": (
                    "F > 20% is typically considered acceptable for small molecule drugs. "
                    "F ≥ 80% is required for bioequivalence studies. "
                    "Low F may indicate poor absorption, first-pass metabolism, or low solubility."
                ),
            },
            "metadata": {
                "source": "Local calculation",
                "method": "Dose-normalized AUC ratio (Rowland & Tozer, 2011)",
            },
        }
