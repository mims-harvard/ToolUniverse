"""
GBIF_get_taxon_children

List the direct child taxa of a GBIF Backbone taxon. Given a taxonKey (e.g. a genus), returns its...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GBIF_get_taxon_children(
    taxon_key: int,
    limit: Optional[int] = 20,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List the direct child taxa of a GBIF Backbone taxon. Given a taxonKey (e.g. a genus), returns its...

    Parameters
    ----------
    taxon_key : int
        GBIF Backbone usageKey of the parent taxon, e.g. 2435194 (genus Panthera). Ob...
    limit : int
        Maximum number of child taxa to return (1-100, default 20).
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
        for k, v in {"taxon_key": taxon_key, "limit": limit}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GBIF_get_taxon_children",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GBIF_get_taxon_children"]
