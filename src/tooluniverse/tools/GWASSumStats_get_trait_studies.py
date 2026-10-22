"""
GWASSumStats_get_trait_studies

Get GWAS studies with deposited summary statistics for a specific EFO trait. Use start/size pagin...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GWASSumStats_get_trait_studies(
    trait_id: str,
    size: Optional[int] = None,
    start: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get GWAS studies with deposited summary statistics for a specific EFO trait. Use start/size pagin...

    Parameters
    ----------
    trait_id : str
        EFO trait ontology ID (e.g., 'EFO_0000249' for Alzheimer disease, 'EFO_000164...
    size : int
        Studies per page (default 20, max 1000).
    start : int
        Zero-based start offset (default 0). Continue with metadata.next_start.
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
        for k, v in {"trait_id": trait_id, "size": size, "start": start}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GWASSumStats_get_trait_studies",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GWASSumStats_get_trait_studies"]
