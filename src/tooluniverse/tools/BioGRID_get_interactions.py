"""
BioGRID_get_interactions

Query experimentally validated protein and genetic interactions from BioGRID (Biological General ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BioGRID_get_interactions(
    gene_names: Optional[list[str]] = None,
    gene_name: Optional[str] = None,
    organism: Optional[str] = "9606",
    interaction_type: Optional[str] = "both",
    evidence_types: Optional[list[str]] = None,
    limit: Optional[int] = 100,
    throughput: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Query experimentally validated protein and genetic interactions from BioGRID (Biological General ...

    Parameters
    ----------
    gene_names : list[str]
        List of gene names or protein identifiers (e.g., ['TP53', 'BRCA1', 'MYC']). A...
    gene_name : str
        Alias for gene_names: single gene symbol (e.g., 'TP53'). Converted to gene_na...
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
    Any
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "gene_names": gene_names,
            "gene_name": gene_name,
            "organism": organism,
            "interaction_type": interaction_type,
            "evidence_types": evidence_types,
            "limit": limit,
            "throughput": throughput,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "BioGRID_get_interactions",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BioGRID_get_interactions"]
