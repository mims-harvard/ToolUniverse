"""
SIGNOR_connect_proteins

Find the curated causal signaling sub-network that connects a set of proteins in the SIGNOR datab...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SIGNOR_connect_proteins(
    proteins: list[str],
    level: Optional[int] = 2,
    limit: Optional[int] = 200,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Find the curated causal signaling sub-network that connects a set of proteins in the SIGNOR datab...

    Parameters
    ----------
    proteins : list[str]
        List of two or more UniProt accessions to connect (e.g., ['P29317', 'Q06124',...
    level : int
        Path depth for connecting the proteins: 1 (direct interactions only), 2 (allo...
    limit : int
        Maximum number of interactions to return.
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
        for k, v in {"proteins": proteins, "level": level, "limit": limit}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "SIGNOR_connect_proteins",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SIGNOR_connect_proteins"]
