"""
ChEBI_get_ontology_children

Get the ontology children (is-a, has-part, has-functional-parent, etc.) of a ChEBI compound. ChEB...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ChEBI_get_ontology_children(
    chebi_id: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the ontology children (is-a, has-part, has-functional-parent, etc.) of a ChEBI compound. ChEB...

    Parameters
    ----------
    chebi_id : int
        ChEBI numeric identifier (without 'CHEBI:' prefix). Examples: 15365 (aspirin)...
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
    _args = {k: v for k, v in {"chebi_id": chebi_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "ChEBI_get_ontology_children",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ChEBI_get_ontology_children"]
