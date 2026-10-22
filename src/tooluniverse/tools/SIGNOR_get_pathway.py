"""
SIGNOR_get_pathway

Get signaling interactions in a SIGNOR curated pathway. Results are recoverably paginated: start ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SIGNOR_get_pathway(
    pathway_id: str,
    limit: Optional[int] = 100,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get signaling interactions in a SIGNOR curated pathway. Results are recoverably paginated: start ...

    Parameters
    ----------
    pathway_id : str
        SIGNOR pathway identifier (e.g., 'SIGNOR-AD' for Alzheimer, 'SIGNOR-AML' for ...
    limit : int
        Maximum number of interactions to return.
    offset : int
        Zero-based pathway-interaction offset. Continue with metadata.next_offset.
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
        for k, v in {"pathway_id": pathway_id, "limit": limit, "offset": offset}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "SIGNOR_get_pathway",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SIGNOR_get_pathway"]
