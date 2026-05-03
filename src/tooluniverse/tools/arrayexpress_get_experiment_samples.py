"""
arrayexpress_get_experiment_samples

Get sample information for an ArrayExpress experiment. Returns sample metadata including sample n...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def arrayexpress_get_experiment_samples(
    experiment_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get sample information for an ArrayExpress experiment. Returns sample metadata including sample n...

    Parameters
    ----------
    experiment_id : str
        ArrayExpress experiment ID
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {"experiment_id": experiment_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "arrayexpress_get_experiment_samples",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["arrayexpress_get_experiment_samples"]
