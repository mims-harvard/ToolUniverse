"""
proteins_api_get_variants

Get variation data for a protein including disease-associated variants, natural variants, and pop...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def proteins_api_get_variants(
    accession: str | list[Any],
    size: Optional[int] = 100,
    offset: Optional[int] = 0,
    format: Optional[str] = "json",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get variation data for a protein including disease-associated variants, natural variants, and pop...

    Parameters
    ----------
    accession : str | list[Any]
        UniProt protein accession(s). Can be a single accession (e.g., 'P05067'), com...
    size : int
        Maximum number of variants to return per protein (default: 100)
    offset : int
        Offset for pagination (default: 0)
    format : str
        Response format. JSON is recommended for most use cases.
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
            "accession": accession,
            "size": size,
            "offset": offset,
            "format": format,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "proteins_api_get_variants",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["proteins_api_get_variants"]
