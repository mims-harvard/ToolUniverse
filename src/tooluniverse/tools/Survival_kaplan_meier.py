"""
Survival_kaplan_meier

Compute Kaplan-Meier survival estimates from time-to-event data. Returns survival probability at ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Survival_kaplan_meier(
    operation: str,
    durations: list[Any],
    event_observed: list[Any],
    group_labels: Optional[list[str] | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Compute Kaplan-Meier survival estimates from time-to-event data. Returns survival probability at ...

    Parameters
    ----------
    operation : str
        Operation type
    durations : list[Any]
        Observed time durations (e.g., months to event or censoring). All values must...
    event_observed : list[Any]
        Event indicator: 1 = event occurred (death/relapse), 0 = censored. Same lengt...
    group_labels : list[str] | Any
        Optional group labels for stratified KM analysis (e.g., ['high', 'low', 'high...
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

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {
        "operation": operation,
                "durations": durations,
                "event_observed": event_observed,
                "group_labels": group_labels
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "Survival_kaplan_meier",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["Survival_kaplan_meier"]
