"""
ExpressionAtlas_get_experiment

Get detailed metadata for a specific Expression Atlas experiment by accession (e.g., E-MTAB-2836)...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ExpressionAtlas_get_experiment(
    accession: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Optional[dict[str, Any]]:
    """
    Get detailed metadata for a specific Expression Atlas experiment by accession (e.g., E-MTAB-2836)...

    Parameters
    ----------
    accession : str
        Expression Atlas experiment accession (e.g., 'E-MTAB-2836', 'E-GEOD-26284')
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    Optional[dict[str, Any]]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {"accession": accession}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "ExpressionAtlas_get_experiment",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ExpressionAtlas_get_experiment"]
