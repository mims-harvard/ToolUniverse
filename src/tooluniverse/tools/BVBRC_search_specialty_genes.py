"""
BVBRC_search_specialty_genes

Search for specialty genes in BV-BRC including virulence factors, antibiotic resistance genes, dr...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BVBRC_search_specialty_genes(
    gene: Optional[str | Any] = None,
    property: Optional[str | Any] = None,
    source: Optional[str | Any] = None,
    taxon_id: Optional[str | Any] = None,
    limit: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search for specialty genes in BV-BRC including virulence factors, antibiotic resistance genes, dr...

    Parameters
    ----------
    gene : str | Any
        Gene name to search. Examples: 'mecA' (methicillin resistance), 'katG' (isoni...
    property : str | Any
        Specialty gene property category. Options: 'Antibiotic Resistance', 'Virulenc...
    source : str | Any
        Source database for annotation. Options: 'CARD', 'NDARO', 'PATRIC_VF', 'VFDB'...
    taxon_id : str | Any
        NCBI Taxonomy ID. Examples: '1280' (S. aureus), '1773' (M. tuberculosis), '56...
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

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "gene": gene,
            "property": property,
            "source": source,
            "taxon_id": taxon_id,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "BVBRC_search_specialty_genes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BVBRC_search_specialty_genes"]
