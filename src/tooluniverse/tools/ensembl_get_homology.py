"""
ensembl_get_homology

Get homology (orthologues and paralogues) for a gene by symbol across species. Returns evolutiona...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ensembl_get_homology(
    species: str,
    symbol: str,
    target_species: Optional[str] = None,
    target_taxon: Optional[str] = None,
    type_: Optional[str] = "all",
    sequence: Optional[str] = "none",
    aligned: Optional[bool] = False,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get homology (orthologues and paralogues) for a gene by symbol across species. Returns evolutiona...

    Parameters
    ----------
    species : str
        Source species (e.g., 'human', 'homo_sapiens')
    symbol : str
        Gene symbol (e.g., 'BRCA2', 'TP53')
    target_species : str
        Target species to find homologues in (optional, e.g., 'mouse', 'mus_musculus'...
    target_taxon : str
        Target taxonomic group (optional, e.g., 'Mammalia', 'Primates')
    type_ : str
        Homology type: 'orthologues' (different species), 'paralogues' (same species)...
    sequence : str
        Include sequences in response
    aligned : bool
        Return aligned sequences
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
            "name": "ensembl_get_homology",
            "arguments": {
                "species": species,
                "symbol": symbol,
                "target_species": target_species,
                "target_taxon": target_taxon,
                "type": type_,
                "sequence": sequence,
                "aligned": aligned,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ensembl_get_homology"]
