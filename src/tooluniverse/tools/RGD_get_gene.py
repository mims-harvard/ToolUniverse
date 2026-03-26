"""
RGD_get_gene

Get detailed rat gene information from the Rat Genome Database by RGD ID. Returns gene symbol, na...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def RGD_get_gene(
    rgd_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed rat gene information from the Rat Genome Database by RGD ID. Returns gene symbol, na...

    Parameters
    ----------
    rgd_id : str
        RGD gene ID (numeric, e.g., '2218' for Brca1). Can include 'RGD:' prefix.
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
    _args = {k: v for k, v in {"rgd_id": rgd_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "RGD_get_gene",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["RGD_get_gene"]
