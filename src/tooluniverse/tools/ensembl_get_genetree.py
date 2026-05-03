"""
ensembl_get_genetree

Get gene tree (phylogenetic tree) for a gene. Returns evolutionary relationships showing ortholog...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ensembl_get_genetree(
    id: str,
    prune_species: Optional[str] = None,
    prune_taxon: Optional[str] = None,
    aligned: Optional[bool] = False,
    sequence: Optional[str] = "none",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get gene tree (phylogenetic tree) for a gene. Returns evolutionary relationships showing ortholog...

    Parameters
    ----------
    id : str
        Gene tree ID (e.g., 'ENSGT00390000003602'). Gene tree IDs can be found in gen...
    prune_species : str
        Prune tree to specific species (optional, e.g., 'homo_sapiens,mus_musculus')
    prune_taxon : str
        Prune tree to specific taxon (optional)
    aligned : bool
        Return aligned sequences
    sequence : str
        Include sequences in tree (cdna, protein, or none)
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "id": id,
            "prune_species": prune_species,
            "prune_taxon": prune_taxon,
            "aligned": aligned,
            "sequence": sequence,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ensembl_get_genetree",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ensembl_get_genetree"]
