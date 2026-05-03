"""
BioGRID_get_chemical_interactions

Query experimentally validated interactions for specific genes/proteins from BioGRID, filtered fo...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BioGRID_get_chemical_interactions(
    gene_names: Optional[list[str]] = None,
    chemical_names: Optional[list[str]] = None,
    organism: Optional[str] = "9606",
    interaction_action: Optional[str] = None,
    limit: Optional[int] = 100,
    include_evidence: Optional[bool] = True,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Query experimentally validated interactions for specific genes/proteins from BioGRID, filtered fo...

    Parameters
    ----------
    gene_names : list[str]
        List of gene names to query for chemical interactions (e.g., ['TP53', 'EGFR',...
    chemical_names : list[str]
        List of chemical compound names (e.g., ['Aspirin', 'Metformin', 'Imatinib'])....
    organism : str
        NCBI taxonomy ID (e.g., '9606' for human, '10090' for mouse). Default: 9606
    interaction_action : str
        Filter by interaction action type (e.g., 'inhibitor', 'activator', 'antagonis...
    limit : int
        Maximum number of chemical interactions to return (default: 100, max: 10000)
    include_evidence : bool
        Include detailed evidence and publication information (default: true)
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
            "chemical_names": chemical_names,
            "organism": organism,
            "interaction_action": interaction_action,
            "limit": limit,
            "include_evidence": include_evidence,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "BioGRID_get_chemical_interactions",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BioGRID_get_chemical_interactions"]
