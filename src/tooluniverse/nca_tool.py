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

import math
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

    def _aumc_trapezoid(self, times: "np.ndarray", concs: "np.ndarray") -> float:
        """
        Linear trapezoidal AUMC calculation (area under the first-moment curve).

        AUMC = integral(t * C(t) dt).  Used to compute model-independent MRT:
        MRT_iv = AUMC_0-inf / AUC_0-inf.

        Uses the linear trapezoid rule throughout: each interval contributes
        dt * (t1*C1 + t2*C2) / 2.  This is consistent with most NCA software
        (e.g., Phoenix WinNonlin uses linear AUMC with log-linear AUC).
        """
        aumc = 0.0
        for i in range(len(times) - 1):
            dt = float(times[i + 1] - times[i])
            t1, t2 = float(times[i]), float(times[i + 1])
            c1, c2 = float(concs[i]), float(concs[i + 1])
            aumc += dt * (t1 * c1 + t2 * c2) / 2.0
        return aumc

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
            # Use >= so the Tmax point itself (C_max) is the first point
            # of the terminal regression.  FDA NCA guidance defines the terminal phase
            # as starting AT Tmax (the concentration-time curve begins declining from
            # Cmax).  Using strict > excluded the Cmax point, leaving only the
            # declining portion.  For plateau profiles (multiple tied Cmax values)
            # combined with the Tmax=last-Cmax fix, >= is required to include enough
            # points (≥3) for a valid regression.
            post_tmax = t_valid >= tmax
            if np.sum(post_tmax) >= 3:
                # FDA NCA: use all post-Tmax points for λz estimation
                t_term = t_valid[post_tmax]
                c_term = c_valid[post_tmax]
            else:
                # Insufficient terminal-phase points (< 3): cannot reliably estimate λz.
                # A 2-point regression is a perfect fit by construction (R²=1 always),
                # giving no quality signal.  The caller will emit a terminal_phase_warning.
                return None, None, None
        else:
            n_use = min(n_points, len(t_valid))
            t_term = t_valid[-n_use:]
            c_term = c_valid[-n_use:]

        # If duplicate time points survive into the terminal phase
        # (e.g., re-measured samples at t=1 with different concentrations), the
        # log-linear regression treats them as independent observations.  Two points at
        # the same time but different concentrations pull the slope toward zero, causing
        # lambda_z to be underestimated by as much as 11% in test cases.  Average
        # concentrations at duplicate times before fitting, consistent with FDA NCA
        # guidance that each time point represents a single true concentration.
        unique_times = np.unique(t_term)
        if len(unique_times) < len(t_term):
            # One or more duplicate time points: average concentrations
            averaged_concs = np.array(
                [float(np.mean(c_term[t_term == ut])) for ut in unique_times]
            )
            t_term = unique_times
            c_term = averaged_concs
        if len(t_term) < 2:
            return None, None, None

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

        # NaN/inf in times must be rejected: np.argsort on a NaN-containing array
        # produces undefined ordering, silently propagating NaN through all PK parameters.
        if np.any(~np.isfinite(t)):
            return {
                "status": "error",
                "error": (
                    "Times contain non-finite values (NaN or inf). "
                    "All time values must be finite real numbers. "
                    "Remove or correct the affected time points."
                ),
            }

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

        # Reject all-negative-time profiles: if every time point is negative (pre-dose
        # only), there is no post-administration pharmacokinetic data to analyse.
        # Without a t≥0 anchor, AUC0-t would integrate over the pre-dose window —
        # a physically meaningless result that would be returned silently.
        if not np.any(t >= 0):
            return {
                "status": "error",
                "error": (
                    "All time points are negative (pre-dose only). "
                    "No post-dose data is available for NCA calculation. "
                    "Provide at least one time point at t ≥ 0 (time of dosing or later)."
                ),
            }
        # The minimum-3 check at the top counts ALL time points including
        # pre-dose samples.  Two pre-dose + one post-dose = 3 total passes the guard
        # but yields AUC=0 (single-point trapezoid) silently under status=success.
        # Enforce a minimum of 2 POST-DOSE points for a non-trivial AUC.
        _n_postdose = int(np.sum(t >= 0))
        if _n_postdose < 2:
            return {
                "status": "error",
                "error": (
                    f"Only {_n_postdose} post-dose time point(s) (t ≥ 0) found "
                    f"(total input points: {len(t)}, pre-dose points: {len(t) - _n_postdose}). "
                    "At least 2 post-dose time points are required to compute a "
                    "non-trivial AUC (trapezoidal integration requires ≥2 points)."
                ),
            }

        # Detect duplicate time points: the linear-log trapezoid computes
        # dt = t[i+1] - t[i] = 0 for duplicates, contributing zero area.
        # Duplicate times are often caused by data entry errors or sample labelling
        # issues.  Warn, but continue — AUC may be underestimated.
        duplicate_times = []
        seen = {}
        for ti in t:
            key = float(ti)
            seen[key] = seen.get(key, 0) + 1
        duplicate_times = [k for k, cnt in seen.items() if cnt > 1]

        # Basic parameters
        # Cmax/Tmax must be computed from POST-DOSE samples only (t >= 0).
        # Pre-dose residual drug can exceed the new dose's Cmax, causing Tmax < 0 and
        # cascading into lambda_z (terminal phase selection uses t > Tmax).
        _postdose_mask = t >= 0
        c_post = c[_postdose_mask]
        t_post = t[_postdose_mask]
        # _postdose_mask guarantees len > 0 (all-pre-dose already caught above).
        # When multiple post-dose samples tie at Cmax (plateau profile),
        # np.argmax returns the FIRST index, so Tmax is set to the plateau start.
        # The terminal-slope filter then includes plateau points in the regression,
        # inflating t_half by up to 80% and underestimating lambda_z by up to 44%.
        # Per FDA NCA guidance, Tmax should be the LAST time at Cmax (end of plateau),
        # so that all t ≥ Tmax data genuinely represents the declining terminal phase.
        _cmax_val = np.max(c_post)
        cmax = float(_cmax_val)
        # When all post-dose concentrations are 0 (all BLQ),
        # _cmax_val=0 and np.where(c_post==0)[0][-1] points to the LAST sample,
        # reporting Tmax=last_sample_time (e.g., 24h) — physically meaningless.
        # When Cmax=0, Tmax should be the first post-dose time (t=0 or first sample).
        if cmax == 0.0:
            tmax = float(t_post[0])
        else:
            tmax = float(t_post[np.where(c_post == _cmax_val)[0][-1]])
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
            # T_auc is empty when all positive concentrations are pre-dose
            # (last_pos_idx < first_nonneg_idx). The old code reached t_auc[0] below,
            # raising IndexError: "index 0 is out of bounds for axis 0 with size 0",
            # which was swallowed by the outer except and returned as an opaque message.
            if len(t_auc) == 0:
                return {
                    "status": "error",
                    "error": (
                        "All positive concentrations are pre-dose (t < 0). "
                        "No post-dose positive concentrations found for AUC computation. "
                        "Check that at least one sample with t ≥ 0 has a measurable "
                        "concentration > 0."
                    ),
                }
            pre_dose_times = [float(x) for x in t[:first_nonneg_idx]]
        else:
            # All post-dose concentrations are zero (all BLQ/undetectable).
            # AUC will be 0; use the post-dose observation window for the key label.
            # When pre-dose samples exist, the old code set
            # t_auc = t (the full array including pre-dose times), giving a key like
            # "AUC-2-8" and omitting pre_dose_time_warning. Apply the same
            # first_nonneg_idx filtering as the positive-concentrations path.
            _first_nonneg_idx = int(np.argmax(t >= 0)) if np.any(t >= 0) else 0
            t_auc = t[_first_nonneg_idx:]
            c_auc = c[_first_nonneg_idx:]
            pre_dose_times = [float(x) for x in t[:_first_nonneg_idx]]
        auc0t = self._auc_trapezoid(t_auc, c_auc)
        # AUMC_0-t for later use in model-independent MRT computation.
        aumc0t = self._aumc_trapezoid(t_auc, c_auc)

        # Np.float64 overflow — round(np.float64(huge), 4) multiplies by
        # 10^4 internally, overflowing to np.inf for values near the float max.
        # Guard with an isfinite check immediately after computing AUC.
        if not math.isfinite(float(auc0t)):
            return {
                "status": "error",
                "error": (
                    f"AUC computation resulted in a non-finite value ({float(auc0t)}). "
                    "This typically indicates extremely large concentration or time values. "
                    "Check input data units — rescaling may be required (e.g., ng/mL → μg/mL, "
                    "hours → days)."
                ),
            }

        # Terminal phase parameters — use all post-Tmax points per FDA NCA guidance
        lambda_z, r_sq_terminal, _ = self._estimate_terminal_slope(t, c, tmax=tmax)

        # Round(..., 4) truncates to 0.0 for sub-nanosecond values
        # (e.g., round(5e-5, 4) = 0.0), producing contradictory output (Tlast=0
        # but non-zero AUC or extrapolation_pct). Use full float precision so that
        # extreme-scale profiles are self-consistent.  This matches the lambda_z
        # treatment at line ~376: "Preserve full precision for lambda_z."
        # Additional protection: round(float(x), 4) overflows for x > ~1.79e304
        # because x * 10^4 exceeds the float maximum.  Use full precision (no rounding)
        # for AUC — consistent with the lambda_z / t_half treatment above.
        _auc0t = float(auc0t)
        result = {
            "Cmax": float(cmax),
            "Tmax": float(tmax),
            "Clast": float(clast),
            "Tlast": float(tlast),
            # Key was always "AUC0-X" even when data starts after t=0.
            # If the first time point is > 0, the integral starts there (not at 0),
            # so the key should reflect the actual integration bounds to avoid a 24%+
            # overstatement when the user reads "AUC0-24" but actually gets AUC_2-24.
            # Use t_auc[-1] (actual upper integration bound) instead of
            # tlast (last POSITIVE concentration time). When all concentrations are
            # zero, tlast=0.0 but integration spans 0 to the last observation time.
            # For non-zero profiles t_auc[-1]==tlast, so this is backward compatible.
            f"AUC{float(t_auc[0]):.6g}-{float(t_auc[-1]):.6g}": _auc0t,
            # "AUC0_last" is misleading when data starts after t=0 (no t=0
            # sample), because "0" implies integration from time of dosing (t=0) but
            # the actual integral starts at the first observed time (e.g., t=2).
            # Keep for backward compatibility; add an explanatory note when t[0] > 0.
            "AUC0_last": _auc0t,
            "units": {
                "Cmax": conc_unit,
                "Tmax": time_unit,
                "AUC": f"{conc_unit}·{time_unit}",
            },
        }

        # Clarify that AUC0_last does NOT start at t=0 when first sample > 0.
        if float(t_auc[0]) > 0:
            result["auc_start_note"] = (
                f"AUC integration starts at the first observed post-dose time "
                f"(t={float(t_auc[0]):.6g}), not at t=0 (no sample at dosing time). "
                f"AUC0_last and {float(t_auc[0]):.6g}-{float(t_auc[-1]):.6g} both reflect "
                "AUC from the first sample to Tlast, which underestimates true AUC0-last "
                "by the missing pre-first-sample area."
            )

        # Warn when pre-dose (t < 0) time points were excluded from AUC integration.
        if pre_dose_times:
            result["pre_dose_time_warning"] = (
                f"Pre-dose time points (t < 0) at t={pre_dose_times} were excluded "
                "from AUC integration. AUC0-t is computed from t=0 per FDA/EMA NCA "
                "guidance. Pre-dose samples are retained for visual inspection only."
            )

        # Warn when duplicate time points are present: dt=0 for duplicates means
        # those intervals contribute zero area to the trapezoid, so AUC is
        # underestimated.  This typically indicates a data entry or labelling error.
        if duplicate_times:
            result["duplicate_time_warning"] = (
                f"Duplicate time points detected at t={duplicate_times}. Each duplicate "
                "contributes a zero-width trapezoid interval (area = 0), which may "
                "underestimate AUC. If duplicates fall in the terminal phase, "
                "concentrations at the same time are averaged before lambda_z regression "
                "to prevent slope bias. Check for data entry errors or sample labelling issues."
            )

        # Check monotonicity of post-Tmax concentrations.
        # Non-monotonic profiles (rising concentrations after Tmax) indicate
        # re-absorption, enterohepatic circulation, or assay issues — making
        # terminal slope estimation unreliable.
        valid_mask = c > 0
        t_valid_all = t[valid_mask]
        c_valid_all = c[valid_mask]
        post_tmax_mask = t_valid_all >= tmax  # use >= to match terminal slope
        if np.sum(post_tmax_mask) >= 3:
            c_post = c_valid_all[post_tmax_mask]
            if np.any(np.diff(c_post) > 0):
                result["non_monotonic_terminal_warning"] = (
                    "Post-Tmax concentrations are not monotonically decreasing. "
                    "This may indicate re-absorption, enterohepatic circulation, a secondary "
                    "Cmax, or assay variability. Terminal slope (lambda_z) may be unreliable."
                )

        # Validate dose unconditionally — before the lambda_z branch.
        # The original validation was nested inside `if lambda_z is not None:`,
        # so invalid doses (negative, zero, NaN, inf) were silently accepted when
        # lambda_z could not be estimated (sparse terminal phase data).
        if dose is not None:
            try:
                _dose_early = float(dose)
            except (ValueError, TypeError):
                return {
                    "status": "error",
                    "error": "dose must be a numeric value. Non-numeric dose is not valid.",
                }
            if not math.isfinite(_dose_early):
                return {
                    "status": "error",
                    "error": (
                        f"dose ({_dose_early}) must be a finite positive number. "
                        "NaN and inf are not valid dose values."
                    ),
                }
            if _dose_early <= 0:
                return {
                    "status": "error",
                    "error": (
                        f"dose ({_dose_early}) must be positive (> 0). "
                        "Negative or zero dose is not physically meaningful. "
                        "CL and Vd cannot be computed without a positive dose."
                    ),
                }

        if lambda_z is not None:
            t_half = np.log(2) / lambda_z
            # AUC0-inf = AUC0-t + Clast/λz
            auc0inf = auc0t + clast / lambda_z
            extrap_pct = float((clast / lambda_z) / auc0inf * 100)
            # Preserve full precision for lambda_z: round(1e-9, 9) = 0.0 for any
            # lambda_z < 5e-10 h⁻¹ (t½ > ~1.4 billion hours).  Stored 0.0 contradicts
            # t_half and AUC0-inf (which both use the unrounded lambda_z) — a downstream
            # caller that re-derives t_half from stored lambda_z = 0 would get inf.
            # Use full float precision, consistent with t_half and AUC0-inf.
            result["lambda_z"] = float(lambda_z)
            result["t_half"] = float(t_half)
            result["r_squared_terminal_fit"] = round(float(r_sq_terminal), 4)
            # Emit a terminal_fit_quality_warning when the log-linear terminal
            # phase R² is poor.  _fit_one_compartment already has a similar guard
            # (R² < 0.85), but _compute_parameters never checked its own terminal fit.
            # A poor terminal R² means lambda_z, t_half, AUC0-inf, CL, and Vd are all
            # unreliable — the user should be informed before acting on these values.
            if r_sq_terminal < 0.85:
                warn_level = "Very poor" if r_sq_terminal < 0.5 else "Poor"
                result["terminal_fit_quality_warning"] = (
                    f"{warn_level} terminal-phase fit (R² = {round(r_sq_terminal, 4)} < 0.85). "
                    "lambda_z, t½, AUC0-inf, clearance, and Vd estimates may be unreliable. "
                    "Possible causes: non-log-linear terminal decline (multi-compartment "
                    "kinetics, redistribution), insufficient time points in the terminal "
                    "phase, or assay variability. Consider adding more late time points "
                    "or using a non-compartmental model review."
                )
            result["AUC0-inf"] = float(auc0inf)
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
                    # NaN/inf bypass the <= 0 guard: NaN <= 0 is False, inf > 0.
                    # Both produce invalid CL/Vd (NaN or inf) under status=success.
                    if not math.isfinite(dose_val):
                        return {
                            "status": "error",
                            "error": (
                                f"dose ({dose_val}) must be a finite positive number. "
                                "NaN and inf are not valid dose values."
                            ),
                        }
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
                        # Round(cl_l, 6) silently truncates CL to 0.0 for
                        # any CL < 5e-7 L/time (e.g., rare biotech analytes with tiny
                        # doses in ng).  Use full precision consistent with lambda_z/AUC.
                        result["clearance_CL"] = float(cl_l)
                        result["clearance_CL_unit"] = f"L/{time_unit}"
                        # For non-IV routes, Dose/AUC = CL/F (apparent
                        # clearance), NOT true systemic clearance (which requires IV
                        # data or a known bioavailability F).  Label it clearly so
                        # users don't compare oral and IV CL values without adjustment.
                        # 'infusion' is also an intravenous route
                        # (F=1 by definition); the old `route != "iv"` check incorrectly
                        # labeled IV infusion clearance as CL/F (apparent clearance).
                        if route not in ("iv", "infusion"):
                            result["clearance_note"] = (
                                "clearance_CL is CL/F (apparent clearance) for non-IV "
                                f"route='{route}'. True systemic CL = CL/F × F, where "
                                "bioavailability F is unknown without an IV reference. "
                                "Do not compare directly with IV-derived clearance."
                            )
                        # 'infusion' is an IV route (F=1), so Vd
                        # and MRT_iv are just as valid for infusion as for iv bolus.
                        # The clearance_note guard already uses ("iv", "infusion");
                        # the Vd/MRT block was never updated to match.
                        if route in ("iv", "infusion"):
                            vd_l = cl_l / lambda_z  # L
                            # Round(vd_l, 4) truncates Vd to 0.0 for any
                            # Vd < 5e-5 L.  Use full precision (same rationale as CL).
                            result["volume_distribution_Vd"] = float(vd_l)
                            result["Vd_unit"] = "L"
                            # MRT_iv = AUMC_0-inf / AUC_0-inf (model-independent NCA).
                            # The previous formula 1/lambda_z is only valid for a
                            # mono-exponential model.  For multi-compartment profiles the
                            # error can reach 10%+.  AUMC_0-inf = AUMC_0-t + Clast*(tlast/λz + 1/λz²).
                            _aumc0inf = float(aumc0t) + clast * (
                                tlast / lambda_z + 1.0 / lambda_z**2
                            )
                            _mrt_iv = (
                                _aumc0inf / float(auc0inf)
                                if float(auc0inf) > 0
                                else None
                            )
                            if _mrt_iv is not None:
                                result["MRT_iv"] = round(_mrt_iv, 4)
                    else:
                        cl = dose_val / auc0inf
                        # Round(float(cl), 6) silently truncates
                        # CL to 0.0 for any CL < 5e-7.  The identical fix was applied
                        # to the known-units path (line ~625: float(cl_l) full precision)
                        # but was never ported here.  Use full float precision.
                        result["clearance_CL"] = float(cl)
                        result["clearance_CL_unit"] = (
                            f"{dose_unit}/({conc_unit}·{time_unit})"
                        )
                        result["pk_unit_note"] = (
                            f"Automatic unit conversion not available for "
                            f"dose_unit='{dose_unit}' / conc_unit='{conc_unit}'. "
                            "CL and Vd are in raw ratio units; convert manually."
                        )
                        # Same infusion fix for unknown-units path.
                        if route in ("iv", "infusion"):
                            vd = cl / lambda_z
                            # Same full-precision fix for Vd.
                            result["volume_distribution_Vd"] = float(vd)
                            result["Vd_unit"] = f"{dose_unit}/{conc_unit}"
                            # MRT_iv = AUMC_0-inf / AUC_0-inf (model-independent NCA).
                            # The previous formula 1/lambda_z is only valid for a
                            # mono-exponential model.  For multi-compartment profiles the
                            # error can reach 10%+.  AUMC_0-inf = AUMC_0-t + Clast*(tlast/λz + 1/λz²).
                            _aumc0inf = float(aumc0t) + clast * (
                                tlast / lambda_z + 1.0 / lambda_z**2
                            )
                            _mrt_iv = (
                                _aumc0inf / float(auc0inf)
                                if float(auc0inf) > 0
                                else None
                            )
                            if _mrt_iv is not None:
                                result["MRT_iv"] = round(_mrt_iv, 4)
                except (ValueError, TypeError):
                    pass
        else:
            result["terminal_phase_warning"] = (
                "Could not estimate terminal slope (λz). "
                "Add more time points in the terminal elimination phase."
            )

        # When the first sample is at t > 0, AUC0-inf is
        # underestimated (the pre-first-sample area is missing).  CL = Dose/AUC0-inf,
        # Vd = CL/λz, and MRT = AUMC0-inf/AUC0-inf are all derived from AUC0-inf
        # and therefore carry the same bias.  The existing auc_start_note documents
        # the AUC issue; this note explicitly flags the downstream PK parameters so
        # users who read only CL/Vd/MRT are not misled.
        if float(t_auc[0]) > 0 and any(
            k in result for k in ("clearance_CL", "volume_distribution_Vd", "MRT_iv")
        ):
            result["derived_pk_bias_note"] = (
                f"clearance_CL, volume_distribution_Vd, and MRT_iv are derived from "
                f"AUC0-inf, which is underestimated because the first observed sample "
                f"is at t={float(t_auc[0]):.6g} (not t=0). The missing pre-first-sample "
                "area causes CL and Vd to be overestimated and MRT to be biased. "
                "Include a sample at or near t=0, or apply compartmental modelling, "
                "to obtain accurate CL, Vd, and MRT."
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

        # Validate times array: NaN in times gives a misleading "mono-exponential
        # decline" error from curve_fit instead of the true cause.
        if np.any(~np.isfinite(t)):
            return {
                "status": "error",
                "error": (
                    "Times contain non-finite values (NaN or inf). "
                    "All time values must be finite real numbers. "
                    "Remove or correct the affected time points."
                ),
            }

        # Validate concentration array (consistent with _compute_parameters).
        if np.any(~np.isfinite(c)):
            return {
                "status": "error",
                "error": (
                    "Concentrations contain non-finite values (NaN or inf). "
                    "Replace with valid measured values."
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

        # Use positive concentrations at non-negative times only.
        # Pre-dose (t < 0) data points represent baseline/endogenous levels
        # and should not be included in a mono-exponential IV bolus fit.  The original
        # `valid = c > 0` silently included negative-time data, biasing the C0 and
        # k_el estimates.  FDA/EMA NCA guidance excludes pre-dose samples from PK fitting.
        valid = (c > 0) & (t >= 0)
        if sum(valid) < 3:
            return {
                "status": "error",
                "error": "At least 3 positive concentration values required for model fitting",
            }

        t_fit = t[valid]
        c_fit = c[valid]

        # All-identical time values make exponential fitting
        # degenerate — the optimizer receives five observations all at the same
        # independent-variable value and returns an arbitrary k_el. Detect this
        # and return a clear error rather than a misleading result.
        if np.ptp(t_fit) == 0.0:  # peak-to-peak range == 0 means all times equal
            return {
                "status": "error",
                "error": (
                    "All time values are identical "
                    f"(t = {float(t_fit[0])} for all {int(sum(valid))} positive "
                    "concentration points). At least two distinct time points are "
                    "required to estimate an elimination rate constant."
                ),
            }

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
        # `1.0 - ss_res/ss_tot` can produce -0.0 (IEEE-754
        # negative zero) when ss_res ≈ ss_tot.  Apply the same `+ 0.0` pattern
        # used by DoseResponse to eliminate negative zero from JSON output.
        r_squared = (float(1.0 - ss_res / ss_tot) + 0.0) if ss_tot > 0 else 0.0

        if r_squared >= 0.95:
            gof = "Good (R²≥0.95)"
        elif r_squared >= 0.85:
            gof = "Moderate (0.85≤R²<0.95)"
        else:
            gof = "Poor (R²<0.85) — consider multi-compartment model"

        # Preserve full precision for k_el: round(1e-9, 6) = 0.0, which is wrong
        # for drugs near the lower optimization bound (1e-9 h⁻¹ ≡ t½ ≈ 693M h).
        # Same applies to t_half: round(float(t_half), 4) = 0.0 for sub-ns half-lives.
        k_el_val = float(k_el_fit)
        # SE of k_el needs same precision to avoid reporting 0.0.
        k_el_se_val = float(perr[1])

        result = {
            "model": "1-compartment IV bolus",
            "equation": "C(t) = C0 × exp(-k_el × t)",
            "C0_initial_concentration": round(float(c0_fit), 4),
            "k_el_elimination_rate": k_el_val,
            "t_half": float(t_half),
            # Apply + 0.0 AFTER round() because round() of a tiny
            # negative value (e.g. -1e-17) produces -0.0 in IEEE-754 arithmetic.
            # The + 0.0 at the computation site (line above) eliminates -0.0 from the
            # variable, but round(-tiny, 4) can produce -0.0 afresh.
            "r_squared": round(r_squared, 4) + 0.0,
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

        # Emit a structured fit_quality_warning for poor fits (R² < 0.85).
        # The goodness_of_fit label transitions at 0.85/0.95, so R² < 0.85 is
        # already labelled "Poor". Providing a machine-readable field allows
        # programmatic callers to detect and flag poor fits without parsing strings.
        # Threshold aligns with the existing "Poor (R²<0.85)" label.
        if r_squared < 0.85:
            if r_squared < 0.1:
                fit_warn_msg = (
                    f"Very poor fit (R² = {round(r_squared, 4) + 0.0}): the 1-compartment "
                    "model explains < 10% of the variance in the concentration data. "
                    "This often indicates a flat profile (no measurable elimination "
                    "over the sampling window), highly noisy data, or a multi-phasic "
                    "decline. The t½ and k_el estimates are unreliable."
                )
            else:
                fit_warn_msg = (
                    f"Poor fit (R² = {round(r_squared, 4) + 0.0} < 0.85): the 1-compartment "
                    "model does not describe the data well. Consider a 2-compartment "
                    "model or non-compartmental analysis. The t½ and k_el estimates "
                    "should be interpreted with caution."
                )
            result["fit_quality_warning"] = fit_warn_msg

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
                # NaN/inf bypass the <= 0 guard: NaN <= 0 is False, inf > 0.
                if not math.isfinite(dose_val):
                    return {
                        "status": "error",
                        "error": (
                            f"dose ({dose_val}) must be a finite positive number. "
                            "NaN and inf are not valid dose values."
                        ),
                    }
                # Validate dose: zero or negative doses are not physically meaningful.
                if dose_val <= 0:
                    return {
                        "status": "error",
                        "error": (
                            f"dose ({dose_val}) must be positive (> 0). "
                            "Zero or negative doses are not physically meaningful. "
                            "Vd and CL cannot be computed without a positive dose."
                        ),
                    }
                auc0inf = c0_fit / k_el_fit
                dose_ng, conc_factor, converted = self._try_pk_unit_conversion(
                    dose_val, dose_unit, conc_unit
                )
                if converted:
                    c0_ng_per_ml = c0_fit * conc_factor
                    vd_ml = dose_ng / c0_ng_per_ml  # mL
                    vd_l = vd_ml / 1000.0  # L
                    cl_l = k_el_fit * vd_l  # L/time_unit
                    # Round(vd_l, 4) silently truncates Vd to
                    # 0.0 for any Vd < 5e-5 L (e.g., 1 ng dose ÷ 100 ng/mL = 1e-5 L).
                    # The _compute_parameters path already uses float(vd_l) (full
                    # precision); apply the identical fix here.
                    result["volume_distribution_Vd"] = float(vd_l)
                    result["Vd_unit"] = "L"
                    result["clearance_CL"] = float(cl_l)
                    result["CL_unit"] = f"L/{time_unit}"
                else:
                    vd_raw = dose_val / c0_fit
                    cl_raw = k_el_fit * vd_raw
                    # Same full-precision fix for unknown-units path.
                    result["volume_distribution_Vd"] = float(vd_raw)
                    result["Vd_unit"] = f"{dose_unit}/{conc_unit}"
                    result["clearance_CL"] = float(cl_raw)
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

        # Validate all inputs are finite (guards against inf propagating to F=inf).
        for name, val in [
            ("auc_po", auc_po),
            ("dose_po", dose_po),
            ("auc_iv", auc_iv),
            ("dose_iv", dose_iv),
        ]:
            if not np.isfinite(val):
                return {
                    "status": "error",
                    "error": f"{name} must be a finite number (received {val}).",
                }

        if auc_po < 0:
            return {
                "status": "error",
                "error": (
                    f"auc_po ({auc_po}) must be non-negative. "
                    "A negative AUC is not physically meaningful."
                ),
            }

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

        # F > 1.0 (> 100%) is physically unusual for most drugs.
        # While theoretically possible (e.g., saturable first-pass extraction reversal,
        # IV formulation with poor tolerability requiring dose reduction), it more
        # commonly indicates mismatched dose units or a data entry error.
        anomalous_f_warning = None
        if f > 1.0:
            anomalous_f_warning = (
                f"Bioavailability F = {f_pct:.2f}% (> 100%). This is physically unusual "
                "for most small molecule drugs. Common causes include: (1) mismatched AUC "
                "or dose units between the PO and IV arms, (2) different dose levels "
                "triggering saturable first-pass extraction, or (3) a data entry error. "
                "Verify that AUC_PO, AUC_IV, dose_PO, and dose_IV are expressed in "
                "consistent units."
            )

        result_data: dict = {
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
        }
        if anomalous_f_warning:
            result_data["anomalous_f_warning"] = anomalous_f_warning

        return {
            "status": "success",
            "data": result_data,
            "metadata": {
                "source": "Local calculation",
                "method": "Dose-normalized AUC ratio (Rowland & Tozer, 2011)",
            },
        }
