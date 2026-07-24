"""
MaveDB_get_mapped_variants

Get genomically-mapped variant coordinates (GA4GH VRS Allele + ClinGen Allele ID) for a MaveDB sc...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MaveDB_get_mapped_variants(
    urn: str,
    limit: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get genomically-mapped variant coordinates (GA4GH VRS Allele + ClinGen Allele ID) for a MaveDB sc...

    Parameters
    ----------
    urn : str
        MaveDB score set URN (e.g., 'urn:mavedb:00001263-a-2' for BRCA2 SGE). Obtain ...
    limit : int
        Maximum number of mapped variants to return (client-side truncation). Set to ...
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
    _args = {k: v for k, v in {"urn": urn, "limit": limit}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "MaveDB_get_mapped_variants",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MaveDB_get_mapped_variants"]
