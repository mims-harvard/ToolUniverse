"""
ChIPAtlas_search_datasets

Search ChIP-Atlas by exactly one of antigen or cell type. Matching metadata rows and the experime...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ChIPAtlas_search_datasets(
    operation: Optional[str] = "search_datasets",
    antigen: Optional[str] = None,
    cell_type: Optional[str] = None,
    genome: Optional[str] = "hg38",
    limit: Optional[int] = 20,
    offset: Optional[int] = 0,
    experiment_id_limit: Optional[int] = 100,
    experiment_id_offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search ChIP-Atlas by exactly one of antigen or cell type. Matching metadata rows and the experime...

    Parameters
    ----------
    operation : str

    antigen : str
        Search by antigen/protein name (e.g., 'CTCF', 'H3K27ac')
    cell_type : str
        Search by cell type (e.g., 'K-562', 'HeLa', 'MCF-7')
    genome : str
        Genome assembly
    limit : int
        Maximum number of matching antigen/cell-type rows to return.
    offset : int
        Zero-based offset into matching antigen/cell-type rows. Continue with data.ne...
    experiment_id_limit : int
        Maximum experiment IDs returned inside each matching row.
    experiment_id_offset : int
        Zero-based experiment-ID offset applied inside each returned row. Repeat the ...
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
            "operation": operation,
            "antigen": antigen,
            "cell_type": cell_type,
            "genome": genome,
            "limit": limit,
            "offset": offset,
            "experiment_id_limit": experiment_id_limit,
            "experiment_id_offset": experiment_id_offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ChIPAtlas_search_datasets",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ChIPAtlas_search_datasets"]
