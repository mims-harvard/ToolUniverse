"""
BVBRC_search_specialty_genes

Search for specialty genes in BV-BRC including virulence factors, antibiotic resistance genes, dr...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BVBRC_search_specialty_genes(
    gene: Optional[str] = None,
    property: Optional[str] = None,
    source: Optional[str] = None,
    taxon_id: Optional[str] = None,
    genome_id: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search for specialty genes in BV-BRC including virulence factors, antibiotic resistance genes, dr...

    Parameters
    ----------
    gene : str
        Gene name to search. Examples: 'mecA' (methicillin resistance), 'katG' (isoni...
    property : str
        Specialty gene property category. Options: 'Antibiotic Resistance', 'Virulenc...
    source : str
        Source database for annotation. Options: 'CARD', 'NDARO', 'PATRIC_VF', 'VFDB'...
    taxon_id : str
        NCBI Taxonomy ID. Examples: '1280' (S. aureus), '1773' (M. tuberculosis), '56...
    genome_id : str
        Exact BV-BRC genome ID, such as '83332.12'. Use this to retrieve specialty ge...
    limit : int
        Maximum number of results per page. Default: 25. Max: 100.
    offset : int
        Zero-based result offset. Use metadata.next_offset to continue.
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
            "genome_id": genome_id,
            "limit": limit,
            "offset": offset,
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
