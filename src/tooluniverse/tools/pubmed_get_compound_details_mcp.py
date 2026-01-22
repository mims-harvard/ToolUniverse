"""
pubmed_get_compound_details_mcp

Get detailed information about a compound by PubChem CID.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def pubmed_get_compound_details_mcp(
    cid: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed information about a compound by PubChem CID.

    Parameters
    ----------
    cid : str
        PubChem Compound ID (e.g., '2244' for aspirin)
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

    return get_shared_client().run_one_function(
        {"name": "pubmed_get_compound_details_mcp", "arguments": {"cid": cid}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["pubmed_get_compound_details_mcp"]
