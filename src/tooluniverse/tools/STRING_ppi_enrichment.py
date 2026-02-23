"""
STRING_ppi_enrichment

Test if your protein set has more interactions than expected by chance (PPI = Protein-Protein Int...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def STRING_ppi_enrichment(
    protein_ids: list[str],
    species: Optional[int] = 9606,
    confidence_score: Optional[float] = 0.4,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Test if your protein set has more interactions than expected by chance (PPI = Protein-Protein Int...

    Parameters
    ----------
    protein_ids : list[str]
        List of protein identifiers (UniProt IDs, gene names, Ensembl IDs). Minimum 3...
    species : int
        NCBI taxonomy ID (default: 9606 for human)
    confidence_score : float
        Minimum confidence score for counting interactions (0-1, default: 0.4)
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
            "name": "STRING_ppi_enrichment",
            "arguments": {
                "protein_ids": protein_ids,
                "species": species,
                "confidence_score": confidence_score,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["STRING_ppi_enrichment"]
