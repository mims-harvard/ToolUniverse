"""
EnsemblCompara_get_orthologues

Find orthologous genes (genes in different species that evolved from a common ancestor) using Ens...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EnsemblCompara_get_orthologues(
    gene: str,
    species: Optional[str] = None,
    target_species: Optional[str] = None,
    target_taxon: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Find orthologous genes (genes in different species that evolved from a common ancestor) using Ens...

    Parameters
    ----------
    gene : str
        Gene symbol or Ensembl gene ID. Examples: 'BRCA1', 'TP53', 'ENSG00000141510',...
    species : str
        Source species (default: 'human'). Examples: 'human', 'mouse', 'zebrafish', '...
    target_species : str
        Target species to limit orthologue search. Examples: 'mouse', 'zebrafish', 'r...
    target_taxon : int
        NCBI taxon ID to limit orthologue search. Examples: 10090 (mouse), 7955 (zebr...
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
            "species": species,
            "target_species": target_species,
            "target_taxon": target_taxon,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EnsemblCompara_get_orthologues",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EnsemblCompara_get_orthologues"]
