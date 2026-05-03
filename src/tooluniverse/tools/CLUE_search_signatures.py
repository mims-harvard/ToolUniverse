"""
CLUE_search_signatures

Search L1000 Connectivity Map perturbation signatures from CLUE.io. Returns perturbation records ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CLUE_search_signatures(
    operation: str,
    pert_type: Optional[str] = None,
    pert_iname: Optional[str] = None,
    limit: Optional[int] = 50,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search L1000 Connectivity Map perturbation signatures from CLUE.io. Returns perturbation records ...

    Parameters
    ----------
    operation : str
        Operation type
    pert_type : str
        Perturbation type filter: 'trt_cp' (compounds), 'trt_oe' (overexpression), 't...
    pert_iname : str
        Perturbagen name to search (partial match). E.g., 'imatinib', 'TP53'
    limit : int
        Maximum number of results to return
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "operation": operation,
            "pert_type": pert_type,
            "pert_iname": pert_iname,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "CLUE_search_signatures",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CLUE_search_signatures"]
