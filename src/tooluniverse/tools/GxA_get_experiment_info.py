"""
GxA_get_experiment_info

Get metadata about a Gene Expression Atlas experiment including species, number of genes and cond...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GxA_get_experiment_info(
    experiment_accession: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get metadata about a Gene Expression Atlas experiment including species, number of genes and cond...

    Parameters
    ----------
    experiment_accession : str
        Expression Atlas experiment accession (e.g., 'E-MTAB-2836', 'E-MTAB-2706', 'E...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    Any
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {"experiment_accession": experiment_accession}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GxA_get_experiment_info",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GxA_get_experiment_info"]
