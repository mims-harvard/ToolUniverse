"""
FDAGSRS_get_substance_relationships

Get the FDA GSRS substance relationship graph plus regulatory references for a substance by UNII....
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FDAGSRS_get_substance_relationships(
    unii: str,
    relationship_type: Optional[str] = None,
    include_references: Optional[bool] = None,
    max_references: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the FDA GSRS substance relationship graph plus regulatory references for a substance by UNII....

    Parameters
    ----------
    unii : str
        FDA UNII (Unique Ingredient Identifier) code. Examples: 'R16CO5Y76E' (aspirin...
    relationship_type : str
        Optional case-insensitive substring filter on relationship type. Examples: 'M...
    include_references : bool
        Whether to include the regulatory/literature references attached to the recor...
    max_references : int
        Maximum number of references to return (1-500, default 100).
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
            "unii": unii,
            "relationship_type": relationship_type,
            "include_references": include_references,
            "max_references": max_references,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "FDAGSRS_get_substance_relationships",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FDAGSRS_get_substance_relationships"]
