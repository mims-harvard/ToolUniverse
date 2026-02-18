"""
BioGRID_get_interactions

Query experimentally validated protein and genetic interactions from BioGRID (Biological General ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BioGRID_get_interactions(
    gene_names: list[str],
    organism: Optional[str] = "9606",
    interaction_type: Optional[str] = "both",
    evidence_types: Optional[list[str]] = None,
    limit: Optional[int] = 100,
    throughput: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Query experimentally validated protein and genetic interactions from BioGRID (Biological General ...

    Parameters
    ----------
    gene_names : list[str]
        List of gene names or protein identifiers (e.g., ['TP53', 'BRCA1', 'MYC']). A...
    organism : str
        Organism name (e.g., 'Homo sapiens', 'Mus musculus') or NCBI taxonomy ID (e.g...
    interaction_type : str
        Type of interaction: 'physical' (protein-protein), 'genetic' (epistasis, synt...
    evidence_types : list[str]
        Filter by evidence types (e.g., ['Affinity Capture-MS', 'Two-hybrid'] for phy...
    limit : int
        Maximum number of interactions to return (default: 100, max: 10000)
    throughput : str
        Filter by throughput: 'low' (low-throughput studies), 'high' (high-throughput...
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

    return get_shared_client().run_one_function(
        {
            "name": "BioGRID_get_interactions",
            "arguments": {
                "gene_names": gene_names,
                "organism": organism,
                "interaction_type": interaction_type,
                "evidence_types": evidence_types,
                "limit": limit,
                "throughput": throughput,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BioGRID_get_interactions"]
