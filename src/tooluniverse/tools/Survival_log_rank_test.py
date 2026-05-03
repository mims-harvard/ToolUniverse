"""
Survival_log_rank_test

Perform Mantel-Cox log-rank test to compare survival between two groups. Tests null hypothesis th...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Survival_log_rank_test(
    operation: str,
    durations_a: list[Any],
    events_a: list[Any],
    durations_b: list[Any],
    events_b: list[Any],
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Perform Mantel-Cox log-rank test to compare survival between two groups. Tests null hypothesis th...

    Parameters
    ----------
    operation : str
        Operation type
    durations_a : list[Any]
        Time durations for group A
    events_a : list[Any]
        Event indicators for group A (1=event, 0=censored)
    durations_b : list[Any]
        Time durations for group B
    events_b : list[Any]
        Event indicators for group B (1=event, 0=censored)
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
    _args = {
        k: v
        for k, v in {
            "operation": operation,
            "durations_a": durations_a,
            "events_a": events_a,
            "durations_b": durations_b,
            "events_b": events_b,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Survival_log_rank_test",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Survival_log_rank_test"]
