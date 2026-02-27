"""
Survival Analysis Tool

Implements Kaplan-Meier estimator, log-rank test, and Cox proportional hazards
regression for survival data analysis.

No external API calls. Uses numpy and scipy for computation.
References: Kaplan & Meier (1958), Mantel (1966), Cox (1972).
"""

import math
from typing import Dict, Any, List
from .base_tool import BaseTool
from .tool_registry import register_tool

try:
    import numpy as np

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    from scipy import stats

    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


@register_tool("SurvivalTool")
class SurvivalTool(BaseTool):
    """
    Local survival analysis tools.

    Implements:
    - Kaplan-Meier survival estimator
    - Log-rank test (Mantel-Cox)
    - Cox proportional hazards regression (basic)

    No external API required. Uses numpy/scipy.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute survival analysis."""
        if not HAS_NUMPY:
            return {
                "status": "error",
                "error": "numpy is required. Install with: pip install numpy scipy",
            }

        operation = arguments.get("operation")
        if not operation:
            return {"status": "error", "error": "Missing required parameter: operation"}

        operation_handlers = {
            "kaplan_meier": self._kaplan_meier,
            "log_rank_test": self._log_rank_test,
            "cox_regression": self._cox_regression,
        }

        handler = operation_handlers.get(operation)
        if not handler:
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}",
                "available_operations": list(operation_handlers.keys()),
            }

        try:
            return handler(arguments)
        except Exception as e:
            return {"status": "error", "error": f"Analysis failed: {str(e)}"}

    def _km_estimator(self, durations: np.ndarray, events: np.ndarray):
        """Compute Kaplan-Meier product-limit survival estimate with Greenwood 95% CI.

        Returns (times, survival, at_risk, events_at_t, n_censored, ci_lower, ci_upper).
        All returned lists have the same length (N+1), with index 0 representing
        the baseline (t=0, S=1, all subjects at risk, zero events/censored).

        95% confidence intervals use the log-log (complementary log-log) transformation,
        the default in R survfit() and recommended by Collett (2015):
            Greenwood sum G = sum_j( d_j / (n_j * (n_j - d_j)) )
            U        = log(-log(S(t)))              (complementary log-log)
            SE_U     = sqrt(G) / |log(S(t))|        (delta method)
            CI       = [S(t)^exp(+1.96*SE_U), S(t)^exp(-1.96*SE_U)]
        Result is naturally in (0, 1) without clamping.
        Edge cases: S=1 → CI=[1,1]; S=0 → CI=[0,0];
        |log(S)| < 1e-10 → plain linear fallback to avoid numerical blow-up.

        References: Collett (2015) Modelling Survival Data in Medical Research, §2.3;
                    Kalbfleisch & Prentice (2002) §1.3.
        """
        event_times = np.sort(np.unique(durations[events == 1]))

        # Include a baseline row (t=0, S=1.0) only when no event occurs at t=0.
        # If the first event time is 0, adding a separate t=0 baseline row would
        # produce duplicate timestamps [0.0, 0.0, ...], which is non-standard and
        # breaks downstream code that assumes unique time points (plots, indexers).
        # Standard KM implementations (R survfit, lifelines) use a single row per
        # unique event time with no duplicate at t=0.
        n_total = int(len(durations))
        has_t0_event = len(event_times) > 0 and float(event_times[0]) == 0.0
        if has_t0_event:
            km_times: List[float] = []
            km_survival: List[float] = []
            km_at_risk: List[int] = []
            km_events: List[int] = []
            km_censored: List[int] = []
            km_ci_lower: List[float] = []
            km_ci_upper: List[float] = []
        else:
            km_times = [0.0]
            km_survival = [1.0]
            km_at_risk = [n_total]
            km_events = [0]
            km_censored = [0]
            km_ci_lower = [1.0]
            km_ci_upper = [1.0]

        s = 1.0
        greenwood_sum = 0.0  # cumulative: Σ dⱼ / (nⱼ × (nⱼ − dⱼ))
        for t_i in event_times:
            n_risk = int(np.sum(durations >= t_i))
            d_i = int(np.sum((durations == t_i) & (events == 1)))
            c_i = int(np.sum((durations == t_i) & (events == 0)))

            # Product-limit update: S(t) *= (1 - d_i / n_risk)
            s *= 1.0 - d_i / n_risk

            # Greenwood variance (Greenwood 1926): accumulate only when n_risk > d_i
            # (if n_risk == d_i, S(t) = 0 and the CI collapses to [0, 0])
            if n_risk > d_i and s > 0:
                greenwood_sum += d_i / (n_risk * (n_risk - d_i))
                log_s = np.log(s)  # always ≤ 0 since 0 < s ≤ 1
                if abs(log_s) < 1e-10:
                    # S very close to 1: SE_U = sqrt(G)/|log(S)| is numerically unstable;
                    # fall back to plain linear Greenwood CI
                    se = s * np.sqrt(greenwood_sum)
                    ci_lower = float(max(0.0, s - 1.96 * se))
                    ci_upper = float(min(1.0, s + 1.96 * se))
                else:
                    # Log-log (complementary log-log) CI — Collett (2015), R survfit default
                    # U = log(-log(S)), SE_U = sqrt(G)/|log(S)|, CI = S^exp(±1.96*SE_U)
                    # because log(-log(·)) is a decreasing function, +z gives the lower bound
                    se_u = np.sqrt(greenwood_sum) / abs(log_s)
                    ci_lower = float(s ** np.exp(+1.96 * se_u))
                    ci_upper = float(s ** np.exp(-1.96 * se_u))
            else:
                ci_lower = 0.0
                ci_upper = 0.0

            km_times.append(float(t_i))
            km_survival.append(round(s, 4))
            km_at_risk.append(n_risk)
            km_events.append(d_i)
            km_censored.append(c_i)
            km_ci_lower.append(round(ci_lower, 4))
            km_ci_upper.append(round(ci_upper, 4))

        return (
            km_times,
            km_survival,
            km_at_risk,
            km_events,
            km_censored,
            km_ci_lower,
            km_ci_upper,
        )

    def _kaplan_meier(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compute Kaplan-Meier survival estimate.

        durations: list of observed times
        event_observed: list of 1 (event occurred) or 0 (censored)
        group_labels: optional list of group labels for stratified analysis
        """
        durations = arguments.get("durations", [])
        event_observed = arguments.get("event_observed", [])

        if not durations or not event_observed:
            return {
                "status": "error",
                "error": "durations and event_observed are required",
            }

        if len(durations) != len(event_observed):
            return {
                "status": "error",
                "error": "durations and event_observed must have the same length",
            }

        group_labels = arguments.get("group_labels")

        try:
            dur = np.array([float(x) for x in durations])
            evs = np.array([int(x) for x in event_observed])
        except (ValueError, TypeError) as e:
            return {"status": "error", "error": f"Invalid values: {e}"}

        # NaN comparison always returns False: np.any(NaN < 0) == False, so NaN
        # bypasses the negative-duration guard and corrupts all downstream
        # at-risk counts and survival probabilities.  Check isfinite first.
        if np.any(~np.isfinite(dur)):
            return {
                "status": "error",
                "error": (
                    "durations contain non-finite values (NaN or inf). "
                    "All survival times must be finite real numbers. "
                    "Remove or correct the affected observations."
                ),
            }

        if np.any(dur < 0):
            return {"status": "error", "error": "All durations must be non-negative"}

        if not np.all(np.isin(evs, [0, 1])):
            return {
                "status": "error",
                "error": "event_observed values must be 0 (censored) or 1 (event occurred)",
            }

        if group_labels is None:
            # Single group
            (
                km_times,
                km_survival,
                km_at_risk,
                km_events,
                km_censored,
                km_ci_lower,
                km_ci_upper,
            ) = self._km_estimator(dur, evs)

            km_surv_arr = np.array(km_survival)
            below = np.where(km_surv_arr <= 0.5)[0]
            median_survival = float(km_times[below[0]]) if len(below) > 0 else None

            return {
                "status": "success",
                "data": {
                    "method": "Kaplan-Meier",
                    "n_subjects": len(dur),
                    "n_events": int(np.sum(evs == 1)),
                    "n_censored": int(np.sum(evs == 0)),
                    "median_survival_time": median_survival,
                    "survival_table": {
                        "times": km_times,
                        "survival_probability": km_survival,
                        "ci_lower_95": km_ci_lower,
                        "ci_upper_95": km_ci_upper,
                        "at_risk": km_at_risk,
                        "events": km_events,
                        "censored": km_censored,
                    },
                    "ci_method": "Greenwood log-log (Collett 2015 / R survfit default)",
                    "follow_up_time": float(np.max(dur)),
                },
            }
        else:
            # Stratified analysis
            if len(group_labels) != len(dur):
                return {
                    "status": "error",
                    "error": "group_labels must have the same length as durations",
                }

            groups = {}
            labels_arr = np.array(group_labels)
            for label in np.unique(labels_arr):
                mask = labels_arr == label
                g_dur = dur[mask]
                g_evs = evs[mask]
                (
                    km_times,
                    km_survival,
                    km_at_risk,
                    km_events,
                    km_censored,
                    km_ci_lower,
                    km_ci_upper,
                ) = self._km_estimator(g_dur, g_evs)

                km_surv_arr = np.array(km_survival)
                below = np.where(km_surv_arr <= 0.5)[0]
                median_survival = float(km_times[below[0]]) if len(below) > 0 else None

                groups[str(label)] = {
                    "n_subjects": int(np.sum(mask)),
                    "n_events": int(np.sum(g_evs)),
                    "n_censored": int(np.sum(mask)) - int(np.sum(g_evs)),
                    "median_survival_time": median_survival,
                    "survival_table": {
                        "times": km_times,
                        "survival_probability": km_survival,
                        "ci_lower_95": km_ci_lower,
                        "ci_upper_95": km_ci_upper,
                        "at_risk": km_at_risk,
                        "events": km_events,
                        "censored": km_censored,
                    },
                }

            return {
                "status": "success",
                "data": {
                    "method": "Kaplan-Meier (stratified)",
                    "ci_method": "Greenwood log-log (Collett 2015 / R survfit default)",
                    "n_groups": len(groups),
                    "groups": groups,
                },
            }

    def _log_rank_test(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform Mantel-Cox log-rank test between two groups.

        durations_a, events_a: Group A survival data
        durations_b, events_b: Group B survival data
        """
        if not HAS_SCIPY:
            return {"status": "error", "error": "scipy is required for log-rank test"}

        for field in ("durations_a", "events_a", "durations_b", "events_b"):
            if not arguments.get(field):
                return {"status": "error", "error": f"{field} is required"}

        try:
            da = np.array([float(x) for x in arguments["durations_a"]])
            ea = np.array([int(x) for x in arguments["events_a"]])
            db = np.array([float(x) for x in arguments["durations_b"]])
            eb = np.array([int(x) for x in arguments["events_b"]])
        except (ValueError, TypeError) as e:
            return {"status": "error", "error": f"Invalid values: {e}"}

        if len(da) != len(ea) or len(db) != len(eb):
            return {
                "status": "error",
                "error": "durations and events must have matching lengths within each group",
            }

        # NaN comparison always returns False, so NaN bypasses all < 0 guards and
        # corrupts at-risk counts, observed/expected events, and the chi2 statistic.
        for arr, name in [
            (da, "durations_a"),
            (db, "durations_b"),
        ]:
            if np.any(~np.isfinite(arr)):
                return {
                    "status": "error",
                    "error": (
                        f"{name} contains non-finite values (NaN or inf). "
                        "All survival times must be finite real numbers."
                    ),
                }

        # Negative survival times are not physically meaningful.
        for arr, name in [(da, "durations_a"), (db, "durations_b")]:
            if np.any(arr < 0):
                return {
                    "status": "error",
                    "error": f"All {name} must be non-negative. Negative survival times are not valid.",
                }

        for arr, name in [(ea, "events_a"), (eb, "events_b")]:
            if not np.all(np.isin(arr, [0, 1])):
                return {
                    "status": "error",
                    "error": f"{name} values must be 0 (censored) or 1 (event occurred)",
                }

        all_times = np.unique(np.concatenate([da[ea == 1], db[eb == 1]]))

        O1_total = O2_total = E1_total = E2_total = 0.0
        var_total = 0.0

        for t in all_times:
            n1 = np.sum(da >= t)
            n2 = np.sum(db >= t)
            o1 = np.sum((da == t) & (ea == 1))
            o2 = np.sum((db == t) & (eb == 1))
            n = n1 + n2
            o = o1 + o2

            if n < 2:
                continue

            e1 = n1 * o / n
            e2 = n2 * o / n

            O1_total += o1
            E1_total += e1
            O2_total += o2
            E2_total += e2

            # Hypergeometric variance
            if n > 1 and o > 0:
                var_total += (n1 * n2 * o * (n - o)) / (n**2 * (n - 1))

        if var_total <= 0:
            # Zero variance occurs when all events share the same time point and the
            # split is proportional (O==E for every stratum).  In this degenerate case
            # chi2 = 0 and p = 1.0 is the correct, well-defined answer: there is no
            # evidence of a difference between the two groups.
            # Use relative tolerance: floating-point sums over many events accumulate
            # rounding errors proportional to total_events × machine epsilon (~2.2e-16),
            # so an absolute threshold of 1e-10 is too tight for studies with thousands
            # of events.  Relative tolerance 1e-8 is safe up to ~10^7 events.
            total_events = O1_total + O2_total
            rel_tol = 1e-8 * max(total_events, 1.0)
            if (
                abs(O1_total - E1_total) <= rel_tol
                and abs(O2_total - E2_total) <= rel_tol
            ):
                chi2_stat = 0.0
                p_value = 1.0
            else:
                return {
                    "status": "error",
                    "error": "Cannot compute log-rank test: zero variance with non-zero observed-expected difference (degenerate data).",
                }
        else:
            chi2_stat = (O1_total - E1_total) ** 2 / var_total
            p_value = 1 - stats.chi2.cdf(chi2_stat, df=1)

        # n_events_in_statistic counts only events that contributed to the chi2.
        # Events at time points where n=n1+n2 < 2 are excluded by the loop guard
        # (hypergeometric variance is 0 when total at-risk < 2). In such cases,
        # n_events_in_statistic < n_events, and the distinction matters for interpretation.
        n_events_in_stat_a = int(round(O1_total))
        n_events_in_stat_b = int(round(O2_total))
        n_events_excluded = (int(np.sum(ea)) - n_events_in_stat_a) + (
            int(np.sum(eb)) - n_events_in_stat_b
        )

        result_data = {
            "method": "Log-Rank Test (Mantel-Cox)",
            "group_a": {
                "n_subjects": len(da),
                "n_events": int(np.sum(ea)),
                "n_events_in_statistic": n_events_in_stat_a,
                "observed": round(float(O1_total), 2),
                "expected": round(float(E1_total), 2),
            },
            "group_b": {
                "n_subjects": len(db),
                "n_events": int(np.sum(eb)),
                "n_events_in_statistic": n_events_in_stat_b,
                "observed": round(float(O2_total), 2),
                "expected": round(float(E2_total), 2),
            },
            "chi2_statistic": round(float(chi2_stat), 4),
            "p_value": round(float(p_value), 6),
            "degrees_of_freedom": 1,
            "interpretation": (
                "Statistically significant difference in survival (p < 0.05)"
                if p_value < 0.05
                else "No statistically significant difference in survival (p >= 0.05)"
            ),
        }
        if n_events_excluded > 0:
            result_data["events_excluded_note"] = (
                f"{n_events_excluded} event(s) were excluded from the chi2 statistic "
                "because at the time of the event, fewer than 2 subjects were at risk "
                "across both groups (hypergeometric variance = 0 at those time points). "
                "n_events_in_statistic reflects only events that contributed to the test."
            )

        return {"status": "success", "data": result_data}

    def _cox_regression(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fit Cox proportional hazards model.

        durations: list of observed times
        event_observed: list of 0/1 event indicators
        covariates: dict of {covariate_name: [values]}
        """
        if not HAS_SCIPY:
            return {"status": "error", "error": "scipy is required for Cox regression"}

        durations = arguments.get("durations", [])
        event_observed = arguments.get("event_observed", [])
        covariates = arguments.get("covariates", {})

        if not durations or not event_observed:
            return {
                "status": "error",
                "error": "durations and event_observed are required",
            }

        if not covariates:
            return {
                "status": "error",
                "error": "covariates dict is required (at least one covariate)",
            }

        try:
            dur = np.array([float(x) for x in durations])
            evs = np.array([int(x) for x in event_observed])
        except (ValueError, TypeError) as e:
            return {"status": "error", "error": f"Invalid duration/event values: {e}"}

        # NaN comparison always returns False, bypassing the < 0 guard below.
        if np.any(~np.isfinite(dur)):
            return {
                "status": "error",
                "error": (
                    "durations contain non-finite values (NaN or inf). "
                    "All survival times must be finite real numbers. "
                    "Remove or correct the affected observations."
                ),
            }

        if np.any(dur < 0):
            return {
                "status": "error",
                "error": "All durations must be non-negative. Negative survival times are not valid.",
            }

        if not np.all(np.isin(evs, [0, 1])):
            return {
                "status": "error",
                "error": "event_observed values must be 0 (censored) or 1 (event occurred)",
            }

        n = len(dur)
        cov_names = list(covariates.keys())
        cov_matrix = []
        for name in cov_names:
            vals = covariates[name]
            if len(vals) != n:
                return {
                    "status": "error",
                    "error": f"Covariate '{name}' has {len(vals)} values but expected {n}",
                }
            try:
                cov_vals = [float(v) for v in vals]
            except (ValueError, TypeError) as e:
                return {
                    "status": "error",
                    "error": f"Invalid values in covariate '{name}': {e}",
                }
            # NaN in a covariate silently propagates through matrix operations, producing
            # NaN gradient and Hessian entries, causing optimization failure with the
            # misleading message "did not converge". Detect and reject upfront.
            if any(not math.isfinite(v) for v in cov_vals):
                return {
                    "status": "error",
                    "error": (
                        f"Covariate '{name}' contains non-finite values (NaN or inf). "
                        "All covariate values must be finite real numbers. "
                        "Impute or remove the affected observations before fitting."
                    ),
                }
            cov_matrix.append(cov_vals)

        X = np.array(cov_matrix).T  # shape (n, p)

        n_events = int(np.sum(evs == 1))
        p = len(cov_names)
        if n_events <= p:
            return {
                "status": "error",
                "error": (
                    f"Cox regression requires the number of events ({n_events}) to "
                    f"exceed the number of covariates ({p}). The partial likelihood "
                    "is not identifiable when events ≤ covariates. Reduce the number "
                    "of covariates or collect more event data."
                ),
            }

        X_mean = X.mean(axis=0)
        X_std = X.std(axis=0)

        # Detect zero-variance covariates (all subjects share the same value).
        # Such covariates carry no information for Cox regression: the partial
        # likelihood is flat, the Hessian is zero, and the resulting standard
        # error is 0/0 = NaN.  Return an informative error immediately instead
        # of propagating NaN (which is also invalid JSON per RFC 8259).
        zero_var_names = [cov_names[i] for i, s in enumerate(X_std) if s == 0]
        if zero_var_names:
            return {
                "status": "error",
                "error": (
                    f"Covariate(s) have zero variance (all subjects share the same value): "
                    f"{zero_var_names}. Cox regression requires variation in each covariate "
                    "to estimate a hazard ratio. Remove the constant covariate(s) before fitting."
                ),
            }

        X_std[X_std == 0] = 1
        X_std_norm = (X - X_mean) / X_std

        # Newton-Raphson optimization for partial likelihood
        beta = np.zeros(X_std_norm.shape[1])

        def partial_log_likelihood(b):
            """Cox partial log-likelihood."""
            eta = X_std_norm @ b
            log_lik = 0.0
            for i in range(n):
                if evs[i] == 1:
                    at_risk = dur >= dur[i]
                    log_lik += eta[i] - np.log(np.sum(np.exp(eta[at_risk])))
            return -log_lik  # minimize negative log-likelihood

        from scipy.optimize import minimize

        result = minimize(
            partial_log_likelihood,
            beta,
            method="L-BFGS-B",
            options={"maxiter": 1000},
        )

        if not result.success:
            return {
                "status": "error",
                "error": "Cox regression optimization did not converge. Try with fewer covariates or more data.",
            }

        beta_fitted = result.x
        beta_original = beta_fitted / X_std

        # Approximate standard errors via Hessian (numerical)
        try:
            from scipy.optimize import approx_fprime

            hess_approx = np.zeros((len(beta_fitted), len(beta_fitted)))
            eps = 1e-5
            for i in range(len(beta_fitted)):

                def grad_i(b):
                    grad = approx_fprime(b, partial_log_likelihood, eps)
                    return grad[i]

                hess_approx[i] = approx_fprime(beta_fitted, grad_i, eps)

            cov_matrix_beta = np.linalg.pinv(hess_approx)
            se = np.sqrt(np.abs(np.diag(cov_matrix_beta)))
        except Exception:
            se = np.full_like(beta_fitted, np.nan)

        # Compute z-scores; guard against division producing NaN if se==0
        # (should not occur after the zero-variance check above, but be safe).
        with np.errstate(invalid="ignore", divide="ignore"):
            z_scores = beta_original / (se / X_std)
        p_values = 2 * (1 - stats.norm.cdf(np.abs(z_scores)))
        # hazard_ratios computed per-covariate below (with overflow guard)

        coef_results = []
        for i, name in enumerate(cov_names):
            p_val = float(p_values[i])
            p_val_out = None if np.isnan(p_val) else round(p_val, 4)
            se_scaled = float(se[i]) / float(X_std[i])

            # Guard CI computation against overflow (complete separation produces a
            # near-singular Hessian → huge se_scaled → exp overflows to inf).
            # Replace non-finite values with None and add a warning.
            with np.errstate(over="ignore"):
                raw_hr = float(np.exp(float(beta_original[i])))
                raw_ci_lo = float(np.exp(float(beta_original[i]) - 1.96 * se_scaled))
                raw_ci_hi = float(np.exp(float(beta_original[i]) + 1.96 * se_scaled))
            separation_warning = None
            if (
                not np.isfinite(raw_hr)
                or not np.isfinite(raw_ci_lo)
                or not np.isfinite(raw_ci_hi)
            ):
                separation_warning = (
                    "Complete or quasi-complete separation detected: the covariate "
                    f"'{name}' perfectly (or nearly perfectly) predicts the outcome. "
                    "The hazard ratio and CI cannot be estimated reliably. Consider "
                    "Firth's penalized regression or exact logistic regression."
                )
            elif (
                np.isfinite(raw_hr)
                and np.isfinite(raw_ci_lo)
                and np.isfinite(raw_ci_hi)
            ):
                # Detect quasi-separation when CI is finite but astronomically wide
                # (e.g., CI lower = 3e-6, CI upper = 1.8e+122): the existing isfinite
                # guard does not fire, yet the estimate is meaningless.
                # Trigger on: HR very small/large, or CI width ratio > 1e6.
                ci_width_ratio = raw_ci_hi / max(raw_ci_lo, 1e-300)
                if raw_hr < 1e-4 or raw_hr > 1e4 or ci_width_ratio > 1e6:
                    separation_warning = (
                        f"Possible quasi-complete separation: the hazard ratio "
                        f"({raw_hr:.4g}) or its 95% CI ({raw_ci_lo:.4g}, {raw_ci_hi:.4g}) "
                        f"is extreme (CI width ratio: {ci_width_ratio:.2g}). "
                        "The coefficient is likely driven by complete separation in the data. "
                        "Consider Firth's penalized regression or adding more event data."
                    )

            # Preserve full precision for HR: round(3.3e-6, 4) = 0.0, which is
            # factually wrong and creates a contradiction when the CI shows a
            # large ratio (indicating a very small HR, not zero).
            hr_out = float(raw_hr) if np.isfinite(raw_hr) else None
            ci_lo_out = float(raw_ci_lo) if np.isfinite(raw_ci_lo) else None
            ci_hi_out = float(raw_ci_hi) if np.isfinite(raw_ci_hi) else None

            entry = {
                "covariate": name,
                "coefficient": round(float(beta_original[i]), 4),
                "hazard_ratio": hr_out,
                "hazard_ratio_95ci": (ci_lo_out, ci_hi_out),
                "p_value": p_val_out,
                "significant": bool(p_val < 0.05) if p_val_out is not None else False,
            }
            if separation_warning:
                entry["separation_warning"] = separation_warning
            coef_results.append(entry)

        return {
            "status": "success",
            "data": {
                "method": "Cox Proportional Hazards",
                "n_subjects": n,
                "n_events": int(np.sum(evs == 1)),
                "coefficients": coef_results,
                "log_likelihood": round(float(-result.fun), 4),
                "convergence": result.success,
                "note": "HR > 1 indicates increased hazard (worse survival); HR < 1 indicates decreased hazard (better survival).",
            },
        }
