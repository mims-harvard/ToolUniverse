"""
Monarch_get_associations

Query disease-gene-phenotype associations in the Monarch Initiative knowledge graph. Find gene-ph...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Monarch_get_associations(
    subject: Optional[str] = None,
    object: Optional[str] = None,
    category: Optional[str] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Query disease-gene-phenotype associations in the Monarch Initiative knowledge graph. Find gene-ph...

    Parameters
    ----------
    subject : str
        Subject entity CURIE. Examples: 'HGNC:11998' (TP53), 'MONDO:0005148' (type 2 ...
    object : str
        Object entity CURIE. Use instead of subject to find entities associated TO th...
    category : str
        Optional Biolink association category filter. Options: 'biolink:GeneToPhenoty...
    limit : int
        Maximum associations to return (default: 20, max: 200).
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
            "object": object,
            "category": category,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Monarch_get_associations",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Monarch_get_associations"]
