"""
Survival_cox_regression

Fit Cox proportional hazards regression model to assess effect of covariates on survival. Returns...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Survival_cox_regression(
    operation: str,
    durations: list[Any],
    event_observed: list[Any],
    covariates: dict[str, Any],
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Fit Cox proportional hazards regression model to assess effect of covariates on survival. Returns...

    Parameters
    ----------
    operation : str
        Operation type
    durations : list[Any]
        Observed time durations
    event_observed : list[Any]
        Event indicators (1=event, 0=censored)
    covariates : dict[str, Any]
        Dict mapping covariate name to array of values. E.g., {'age': [45, 62, ...], ...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    return get_shared_client().run_one_function(
        {
            "name": "Survival_cox_regression",
            "arguments": {
                "operation": operation,
                "durations": durations,
                "event_observed": event_observed,
                "covariates": covariates,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Survival_cox_regression"]
