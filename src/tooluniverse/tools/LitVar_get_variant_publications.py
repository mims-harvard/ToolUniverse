"""
LitVar_get_variant_publications

Get PubMed publication IDs (PMIDs) that mention a specific genetic variant, from NCBI LitVar2. Re...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def LitVar_get_variant_publications(
    rsid: str,
    format: Optional[str] = 'json',
    max: Optional[int] = 50,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get PubMed publication IDs (PMIDs) that mention a specific genetic variant, from NCBI LitVar2. Re...

    Parameters
    ----------
    rsid : str
        dbSNP rsID of the variant (e.g., 'rs328', 'rs7903146', 'rs429358', 'rs80357906')
    format : str
        Response format (default 'json')
    max : int
        Maximum number of PMIDs to return (default 50)
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
    _args = {k: v for k, v in {
        "rsid": rsid,
                "format": format,
                "max": max
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "LitVar_get_variant_publications",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["LitVar_get_variant_publications"]
