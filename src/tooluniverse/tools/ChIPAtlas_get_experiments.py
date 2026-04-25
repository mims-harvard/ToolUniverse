"""
ChIPAtlas_get_experiments

Search ChIP-Atlas experiment metadata including experiment IDs, antigens, cell types, and process...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ChIPAtlas_get_experiments(
    operation: Optional[str] = "get_experiment_list",
    genome: Optional[str] = None,
    antigen: Optional[str] = None,
    cell_type: Optional[str] = None,
    limit: Optional[int] = 100,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search ChIP-Atlas experiment metadata including experiment IDs, antigens, cell types, and process...

    Parameters
    ----------
    operation : str

    genome : str
        Filter by genome assembly
    antigen : str
        Filter by antigen/protein name (e.g., 'CTCF', 'H3K4me3')
    cell_type : str
        Filter by cell type (e.g., 'K-562', 'HepG2', 'CD4')
    limit : int
        Maximum results to return
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
            "genome": genome,
            "antigen": antigen,
            "cell_type": cell_type,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ChIPAtlas_get_experiments",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ChIPAtlas_get_experiments"]
