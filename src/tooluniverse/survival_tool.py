"""
Survival Analysis Tool

Implements Kaplan-Meier estimator, log-rank test, and Cox proportional hazards
regression for survival data analysis.

No external API calls. Uses numpy and scipy for computation.
References: Kaplan & Meier (1958), Mantel (1966), Cox (1972).
"""

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
        """Compute Kaplan-Meier product-limit survival estimate.

        Returns (times, survival, at_risk, events_at_t, n_censored).
        """
        event_times = np.sort(np.unique(durations[events == 1]))

        km_times = [0.0]
        km_survival = [1.0]
        km_at_risk: List[int] = []
        km_events: List[int] = []
        km_censored: List[int] = []

        s = 1.0
        for t_i in event_times:
            n_risk = int(np.sum(durations >= t_i))
            d_i = int(np.sum((durations == t_i) & (events == 1)))
            c_i = int(np.sum((durations == t_i) & (events == 0)))

            # Product-limit update: S(t) *= (1 - d_i / n_risk)
            s *= 1.0 - d_i / n_risk

            km_times.append(float(t_i))
            km_survival.append(round(s, 4))
            km_at_risk.append(n_risk)
            km_events.append(d_i)
            km_censored.append(c_i)

        return km_times, km_survival, km_at_risk, km_events, km_censored

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

        if np.any(dur < 0):
            return {"status": "error", "error": "All durations must be non-negative"}

        if group_labels is None:
            # Single group
            km_times, km_survival, km_at_risk, km_events, km_censored = (
                self._km_estimator(dur, evs)
            )

            km_surv_arr = np.array(km_survival)
            below = np.where(km_surv_arr <= 0.5)[0]
            median_survival = float(km_times[below[0]]) if len(below) > 0 else None

            return {
                "status": "success",
                "data": {
                    "method": "Kaplan-Meier",
                    "n_subjects": len(dur),
                    "n_events": int(np.sum(evs)),
                    "n_censored": int(np.sum(1 - evs)),
                    "median_survival_time": median_survival,
                    "survival_table": {
                        "times": km_times,
                        "survival_probability": km_survival,
                        "at_risk": km_at_risk,
                        "events": km_events,
                        "censored": km_censored,
                    },
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
                km_times, km_survival, km_at_risk, km_events, km_censored = (
                    self._km_estimator(g_dur, g_evs)
                )

                km_surv_arr = np.array(km_survival)
                below = np.where(km_surv_arr <= 0.5)[0]
                median_survival = float(km_times[below[0]]) if len(below) > 0 else None

                groups[str(label)] = {
                    "n_subjects": int(np.sum(mask)),
                    "n_events": int(np.sum(g_evs)),
                    "median_survival_time": median_survival,
                    "survival_table": {
                        "times": km_times,
                        "survival_probability": km_survival,
                    },
                }

            return {
                "status": "success",
                "data": {
                    "method": "Kaplan-Meier (stratified)",
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
            return {
                "status": "error",
                "error": "Cannot compute log-rank test (no variance in event times)",
            }

        chi2_stat = (O1_total - E1_total) ** 2 / var_total
        p_value = 1 - stats.chi2.cdf(chi2_stat, df=1)

        return {
            "status": "success",
            "data": {
                "method": "Log-Rank Test (Mantel-Cox)",
                "group_a": {
                    "n_subjects": len(da),
                    "n_events": int(np.sum(ea)),
                    "observed": round(float(O1_total), 2),
                    "expected": round(float(E1_total), 2),
                },
                "group_b": {
                    "n_subjects": len(db),
                    "n_events": int(np.sum(eb)),
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
            },
        }

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
                cov_matrix.append([float(v) for v in vals])
            except (ValueError, TypeError) as e:
                return {
                    "status": "error",
                    "error": f"Invalid values in covariate '{name}': {e}",
                }

        X = np.array(cov_matrix).T  # shape (n, p)

        X_mean = X.mean(axis=0)
        X_std = X.std(axis=0)
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

        z_scores = beta_original / (se / X_std)
        p_values = 2 * (1 - stats.norm.cdf(np.abs(z_scores)))
        hazard_ratios = np.exp(beta_original)

        coef_results = []
        for i, name in enumerate(cov_names):
            coef_results.append(
                {
                    "covariate": name,
                    "coefficient": round(float(beta_original[i]), 4),
                    "hazard_ratio": round(float(hazard_ratios[i]), 4),
                    "hazard_ratio_95ci": (
                        round(
                            float(np.exp(beta_original[i] - 1.96 * se[i] / X_std[i])), 4
                        ),
                        round(
                            float(np.exp(beta_original[i] + 1.96 * se[i] / X_std[i])), 4
                        ),
                    ),
                    "p_value": round(float(p_values[i]), 4),
                    "significant": bool(p_values[i] < 0.05),
                }
            )

        return {
            "status": "success",
            "data": {
                "method": "Cox Proportional Hazards",
                "n_subjects": n,
                "n_events": int(np.sum(evs)),
                "coefficients": coef_results,
                "log_likelihood": round(float(-result.fun), 4),
                "convergence": result.success,
                "note": "HR > 1 indicates increased hazard (worse survival); HR < 1 indicates decreased hazard (better survival).",
            },
        }
