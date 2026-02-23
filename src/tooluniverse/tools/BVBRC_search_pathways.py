"""
BVBRC_search_pathways

Search for metabolic pathways in pathogen genomes from BV-BRC. Returns KEGG pathway assignments w...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BVBRC_search_pathways(
    taxon_id: Optional[str | Any] = None,
    pathway_name: Optional[str | Any] = None,
    ec_number: Optional[str | Any] = None,
    genome_id: Optional[str | Any] = None,
    limit: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search for metabolic pathways in pathogen genomes from BV-BRC. Returns KEGG pathway assignments w...

    Parameters
    ----------
    taxon_id : str | Any
        NCBI Taxonomy ID. Examples: '1773' (M. tuberculosis), '562' (E. coli), '1280'...
    pathway_name : str | Any
        Pathway name keyword. Examples: 'Glycolysis', 'Fatty acid', 'Amino acid', 'Su...
    ec_number : str | Any
        Enzyme Commission number. Examples: '1.11.1.6' (catalase), '2.7.1.1' (hexokin...
    genome_id : str | Any
        Restrict to a specific genome. Example: '83332.12' (M. tuberculosis H37Rv).
    limit : int | Any
        Maximum number of results. Default: 25. Max: 100.
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

    return get_shared_client().run_one_function(
        {
            "name": "BVBRC_search_pathways",
            "arguments": {
                "taxon_id": taxon_id,
                "pathway_name": pathway_name,
                "ec_number": ec_number,
                "genome_id": genome_id,
                "limit": limit,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BVBRC_search_pathways"]
