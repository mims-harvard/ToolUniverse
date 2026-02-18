"""
BioGRID_get_ptms

Retrieve post-translational modifications (PTM = Protein modifications after translation) for pro...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BioGRID_get_ptms(
    gene_names: list[str],
    organism: Optional[str] = "9606",
    ptm_type: Optional[list[str]] = None,
    residue: Optional[str] = None,
    include_enzymes: Optional[bool] = True,
    include_evidence: Optional[bool] = True,
    limit: Optional[int] = 500,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Retrieve post-translational modifications (PTM = Protein modifications after translation) for pro...

    Parameters
    ----------
    gene_names : list[str]
        List of gene names to query for PTMs (e.g., ['TP53', 'AKT1', 'EGFR', 'ERK1'])...
    organism : str
        NCBI taxonomy ID (e.g., '9606' for human, '10090' for mouse). Default: 9606
    ptm_type : list[str]
        Filter by PTM types (e.g., ['Phosphorylation', 'Ubiquitination', 'Acetylation...
    residue : str
        Filter by specific amino acid residue (e.g., 'S' for serine, 'T' for threonin...
    include_enzymes : bool
        Include information about enzymes responsible for the PTM (kinases, ligases, ...
    include_evidence : bool
        Include experimental evidence and publication details. Default: true
    limit : int
        Maximum number of PTMs to return (default: 500, max: 10000)
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
            "name": "BioGRID_get_ptms",
            "arguments": {
                "gene_names": gene_names,
                "organism": organism,
                "ptm_type": ptm_type,
                "residue": residue,
                "include_enzymes": include_enzymes,
                "include_evidence": include_evidence,
                "limit": limit,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BioGRID_get_ptms"]
