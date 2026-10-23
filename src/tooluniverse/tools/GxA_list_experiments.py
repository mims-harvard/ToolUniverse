"""
GxA_list_experiments

List a resumable page of gene expression experiments from EBI Gene Expression Atlas. Filter by sp...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GxA_list_experiments(
    species: Optional[str] = None,
    experiment_type: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List a resumable page of gene expression experiments from EBI Gene Expression Atlas. Filter by sp...

    Parameters
    ----------
    species : str
        Species name to filter experiments (e.g., 'Homo sapiens', 'Mus musculus', 'Ar...
    experiment_type : str
        Filter by experiment type: 'baseline' (tissue/cell type expression), 'differe...
    limit : int
        Page size (1-100). Default: 20.
    offset : int
        Zero-based experiment offset. Continue with data.next_offset.
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
            "species": species,
            "experiment_type": experiment_type,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GxA_list_experiments",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GxA_list_experiments"]
