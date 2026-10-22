"""
ChEBI_get_compound

Get detailed chemical information from ChEBI, including paginated synonyms, brand names, and syst...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ChEBI_get_compound(
    chebi_id: int | str,
    synonym_offset: Optional[int] = 0,
    synonym_limit: Optional[int] = 20,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed chemical information from ChEBI, including paginated synonyms, brand names, and syst...

    Parameters
    ----------
    chebi_id : int | str
        ChEBI identifier as a bare integer (e.g. 15365) or the 'CHEBI:15365' CURIE fo...
    synonym_offset : int
        Zero-based offset in the deduplicated name list.
    synonym_limit : int
        Names returned per page (default 20, maximum 500).
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
            "chebi_id": chebi_id,
            "synonym_offset": synonym_offset,
            "synonym_limit": synonym_limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ChEBI_get_compound",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ChEBI_get_compound"]
