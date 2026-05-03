"""
MGnify_search_genomes

Search the MGnify genome catalog for metagenome-assembled genomes (MAGs) and isolate genomes. Fil...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MGnify_search_genomes(
    taxonomy: Optional[str] = None,
    genome_type: Optional[str] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the MGnify genome catalog for metagenome-assembled genomes (MAGs) and isolate genomes. Fil...

    Parameters
    ----------
    taxonomy : str
        Taxonomy lineage filter. Examples: 'Firmicutes', 'Bacteroidetes', 'Proteobact...
    genome_type : str
        Filter by genome source type. Options: 'Isolate', 'MAG'.
    page : int
        Page number (default 1).
    page_size : int
        Results per page (default 25, max 100).
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
            "taxonomy": taxonomy,
            "genome_type": genome_type,
            "page": page,
            "page_size": page_size,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MGnify_search_genomes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MGnify_search_genomes"]
