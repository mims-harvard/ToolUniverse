"""
STRING_get_functional_annotations

Get comprehensive functional annotations for a protein from STRING, grouped by category. limit an...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def STRING_get_functional_annotations(
    identifiers: str,
    species: Optional[int] = 9606,
    category: Optional[str] = None,
    limit: Optional[int] = 15,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get comprehensive functional annotations for a protein from STRING, grouped by category. limit an...

    Parameters
    ----------
    identifiers : str
        Protein identifier (gene name or STRING ID). Examples: 'TP53', 'BRCA1', 'EGFR...
    species : int
        NCBI taxonomy ID (default 9606 for human). Examples: 9606 (human), 10090 (mou...
    category : str
        Filter by annotation category. Options: 'Process' (GO BP), 'Function' (GO MF)...
    limit : int
        Page size within each annotation category (default 15).
    offset : int
        Zero-based offset within each annotation category. Continue with category_pag...
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
        for k, v in {
            "identifiers": identifiers,
            "species": species,
            "category": category,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "STRING_get_functional_annotations",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["STRING_get_functional_annotations"]
