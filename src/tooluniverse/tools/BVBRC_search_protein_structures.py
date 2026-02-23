"""
BVBRC_search_protein_structures

Search for pathogen protein structures in BV-BRC by organism (taxon_id), gene name, or experiment...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BVBRC_search_protein_structures(
    taxon_id: Optional[str | Any] = None,
    gene: Optional[str | Any] = None,
    method: Optional[str | Any] = None,
    limit: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search for pathogen protein structures in BV-BRC by organism (taxon_id), gene name, or experiment...

    Parameters
    ----------
    taxon_id : str | Any
        NCBI Taxonomy ID. Examples: '2697049' (SARS-CoV-2), '1773' (M. tuberculosis),...
    gene : str | Any
        Gene name filter. Examples: 'S' (spike), 'rep' (replicase), 'N' (nucleocapsid).
    method : str | Any
        Experimental method. Examples: 'X-ray diffraction', 'Electron microscopy', 'S...
    limit : int | Any
        Maximum number of results. Default: 10. Max: 100.
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
            "name": "BVBRC_search_protein_structures",
            "arguments": {
                "taxon_id": taxon_id,
                "gene": gene,
                "method": method,
                "limit": limit,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BVBRC_search_protein_structures"]
