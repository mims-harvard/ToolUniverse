"""
SCXA_get_cluster_marker_genes

Get EBI Single Cell Expression Atlas computed marker genes per cell cluster (or per cell type) fo...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SCXA_get_cluster_marker_genes(
    experiment_accession: str,
    marker_type: Optional[str] = "clusters",
    k: Optional[int] = None,
    organism_part: Optional[str] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get EBI Single Cell Expression Atlas computed marker genes per cell cluster (or per cell type) fo...

    Parameters
    ----------
    experiment_accession : str
        SCXA experiment accession (e.g. 'E-MTAB-5061', 'E-ENAD-13', 'E-CURD-4'). Use ...
    marker_type : str
        'clusters' for marker genes per cluster at resolution k (default); 'cell_type...
    k : int
        Clustering resolution / number of clusters for marker_type='clusters' (e.g. 8...
    organism_part : str
        Organism part for marker_type='cell_types' (e.g. 'pancreas', 'lung'). Require...
    limit : int
        Optional maximum number of marker rows to return.
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
            "experiment_accession": experiment_accession,
            "marker_type": marker_type,
            "k": k,
            "organism_part": organism_part,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "SCXA_get_cluster_marker_genes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SCXA_get_cluster_marker_genes"]
