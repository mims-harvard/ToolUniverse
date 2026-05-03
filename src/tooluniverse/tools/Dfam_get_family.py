"""
Dfam_get_family

Get detailed information for a specific Dfam transposable element family by accession. Returns co...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Dfam_get_family(
    accession: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed information for a specific Dfam transposable element family by accession. Returns co...

    Parameters
    ----------
    accession : str
        Dfam family accession (e.g., 'DF000000003' for AluSc, 'DF000000053' for AluYa5).
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
    _args = {k: v for k, v in {"accession": accession}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "Dfam_get_family",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Dfam_get_family"]
