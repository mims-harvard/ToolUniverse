"""
BacDive_search_by_taxon

List BacDive strain IDs described for a bacterial or archaeal taxon. BacDive is the DSMZ strain-l...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BacDive_search_by_taxon(
    genus: str,
    species: Optional[str] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List BacDive strain IDs described for a bacterial or archaeal taxon. BacDive is the DSMZ strain-l...

    Parameters
    ----------
    genus : str
        Genus name, capitalized, e.g. 'Bacillus'.
    species : str
        Species epithet, lowercase, e.g. 'subtilis'.
    limit : int
        Maximum strain IDs to return (default 25, max 100).
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
        for k, v in {"genus": genus, "species": species, "limit": limit}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "BacDive_search_by_taxon",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BacDive_search_by_taxon"]
