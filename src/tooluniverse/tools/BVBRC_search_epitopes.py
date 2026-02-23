"""
BVBRC_search_epitopes

Search for pathogen epitopes (B-cell and T-cell) in BV-BRC. Returns epitope sequences, types, pro...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BVBRC_search_epitopes(
    taxon_id: Optional[str | Any] = None,
    protein_name: Optional[str | Any] = None,
    epitope_type: Optional[str | Any] = None,
    organism: Optional[str | Any] = None,
    limit: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search for pathogen epitopes (B-cell and T-cell) in BV-BRC. Returns epitope sequences, types, pro...

    Parameters
    ----------
    taxon_id : str | Any
        NCBI Taxonomy ID for the pathogen organism. Examples: '2697049' (SARS-CoV-2),...
    protein_name : str | Any
        Target protein name to filter epitopes. Examples: 'Spike glycoprotein', 'Nucl...
    epitope_type : str | Any
        Type of epitope. Options: 'Linear peptide', 'Discontinuous peptide'. Most epi...
    organism : str | Any
        Organism name keyword to search across epitope records. Example: 'coronavirus...
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
            "name": "BVBRC_search_epitopes",
            "arguments": {
                "taxon_id": taxon_id,
                "protein_name": protein_name,
                "epitope_type": epitope_type,
                "organism": organism,
                "limit": limit,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BVBRC_search_epitopes"]
