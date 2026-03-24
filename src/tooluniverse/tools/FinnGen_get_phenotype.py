"""
FinnGen_get_phenotype

Get detailed information about a specific FinnGen disease endpoint (phenotype). Returns case/cont...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FinnGen_get_phenotype(
    phenocode: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed information about a specific FinnGen disease endpoint (phenotype). Returns case/cont...

    Parameters
    ----------
    phenocode : str
        FinnGen phenotype code (e.g., 'T2D', 'I9_CHD', 'C3_BREAST', 'J10_ASTHMA'). Ge...
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
    _args = {k: v for k, v in {"phenocode": phenocode}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "FinnGen_get_phenotype",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FinnGen_get_phenotype"]
