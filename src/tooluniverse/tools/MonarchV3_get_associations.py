"""
MonarchV3_get_associations

Query cross-species associations in the Monarch knowledge graph with exact offset pagination. Met...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MonarchV3_get_associations(
    subject: str,
    category: str,
    limit: Optional[int] = 20,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Query cross-species associations in the Monarch knowledge graph with exact offset pagination. Met...

    Parameters
    ----------
    subject : str
        Subject entity CURIE. Examples: 'HGNC:11998' (TP53), 'MONDO:0005148' (type 2 ...
    category : str
        Biolink association category. Options: 'biolink:GeneToPhenotypicFeatureAssoci...
    limit : int
        Associations per page (1-200).
    offset : int
        Zero-based offset. Continue with metadata.next_offset.
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
            "subject": subject,
            "category": category,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MonarchV3_get_associations",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MonarchV3_get_associations"]
