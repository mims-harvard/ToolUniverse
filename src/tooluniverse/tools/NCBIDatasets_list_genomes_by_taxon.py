"""
NCBIDatasets_list_genomes_by_taxon

List genome assemblies available for a taxon (NCBI tax id or scientific name) via the NCBI Datase...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NCBIDatasets_list_genomes_by_taxon(
    taxon: str,
    limit: Optional[int] = None,
    page_token: Optional[str] = None,
    reference_only: Optional[bool] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List genome assemblies available for a taxon (NCBI tax id or scientific name) via the NCBI Datase...

    Parameters
    ----------
    taxon : str
        NCBI tax id or scientific name, e.g. '562', 'Escherichia coli', 'Saccharomyce...
    limit : int
        Assemblies per page (default 20, maximum reliable upstream size 1000).
    page_token : str
        Opaque continuation token from metadata.next_page_token. Omit for the first p...
    reference_only : bool
        If true, return only reference/representative genomes.
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
            "taxon": taxon,
            "limit": limit,
            "page_token": page_token,
            "reference_only": reference_only,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "NCBIDatasets_list_genomes_by_taxon",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NCBIDatasets_list_genomes_by_taxon"]
