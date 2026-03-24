"""
SIGNOR_get_interactions

Get causal signaling interactions for a protein or entity from the SIGNOR database. Returns upstr...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SIGNOR_get_interactions(
    entity_id: str,
    organism: Optional[int] = 9606,
    limit: Optional[int] = 50,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get causal signaling interactions for a protein or entity from the SIGNOR database. Returns upstr...

    Parameters
    ----------
    entity_id : str
        Entity identifier - typically a UniProt accession (e.g., 'P04637' for TP53, '...
    organism : int
        NCBI taxonomy ID. 9606 for human, 10090 for mouse.
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
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "entity_id": entity_id,
            "organism": organism,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "SIGNOR_get_interactions",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SIGNOR_get_interactions"]
