"""
Addgene_get_plasmid

Get detailed information about a specific Addgene plasmid by its catalog ID. Returns full record:...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Addgene_get_plasmid(
    operation: str,
    plasmid_id: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed information about a specific Addgene plasmid by its catalog ID. Returns full record:...

    Parameters
    ----------
    operation : str
        Operation type
    plasmid_id : int
        Addgene plasmid catalog ID (e.g., 39296 for pSpCas9(BB)-2A-Puro, 48138 for pX...
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
        {
            "name": "Addgene_get_plasmid",
            "arguments": {"operation": operation, "plasmid_id": plasmid_id},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Addgene_get_plasmid"]
