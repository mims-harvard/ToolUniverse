"""
DBAASP_get_peptide

Get a full DBAASP antimicrobial peptide record by numeric peptide ID. Returns the sequence, N/C-t...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DBAASP_get_peptide(
    peptideId: int | str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get a full DBAASP antimicrobial peptide record by numeric peptide ID. Returns the sequence, N/C-t...

    Parameters
    ----------
    peptideId : int | str
        DBAASP numeric peptide ID. Example: 107 (Dermaseptin S4 (1-16)[M4K], sequence...
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
    _args = {k: v for k, v in {"peptideId": peptideId}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "DBAASP_get_peptide",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DBAASP_get_peptide"]
