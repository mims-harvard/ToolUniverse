"""
VEuPathDB_search_genes_by_organism

Search genes belonging to an organism/strain in a VEuPathDB member database using the WDK GenesBy...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def VEuPathDB_search_genes_by_organism(
    organism: str,
    project: Optional[str] = None,
    attributes: Optional[list[str] | str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search genes belonging to an organism/strain in a VEuPathDB member database using the WDK GenesBy...

    Parameters
    ----------
    organism : str
        Full organism/strain name as used by VEuPathDB. Examples: 'Plasmodium falcipa...
    project : str
        VEuPathDB member site to query. One of: plasmodb (default), toxodb, fungidb, ...
    attributes : list[str] | str
        Optional list of gene attribute columns to return. Defaults to primary_key, p...
    limit : int
        Maximum number of genes to return (1-500, default 25).
    offset : int
        Zero-based WDK gene result offset. Continue with metadata.next_offset while m...
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
            "organism": organism,
            "project": project,
            "attributes": attributes,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "VEuPathDB_search_genes_by_organism",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["VEuPathDB_search_genes_by_organism"]
