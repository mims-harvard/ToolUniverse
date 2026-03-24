"""
LINCS_search_signatures

Search LINCS (Library of Integrated Network-Based Cellular Signatures) for drug perturbation gene...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def LINCS_search_signatures(
    drug_name: str,
    cell_line: Optional[str] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search LINCS (Library of Integrated Network-Based Cellular Signatures) for drug perturbation gene...

    Parameters
    ----------
    drug_name : str
        Drug or perturbagen name to search for. Case-sensitive, use lowercase for bes...
    cell_line : str
        Optional cell line filter. Examples: 'MCF7', 'A549', 'HepG2', 'PC3'. Leave em...
    limit : int
        Maximum number of signatures to return (1-100). Default: 20.
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
    _args = {
        k: v
        for k, v in {
            "drug_name": drug_name,
            "cell_line": cell_line,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "LINCS_search_signatures",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["LINCS_search_signatures"]
