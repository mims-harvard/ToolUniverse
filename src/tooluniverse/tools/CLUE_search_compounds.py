"""
CLUE_search_compounds

Search chemical compounds (small molecule drugs) in the L1000 Connectivity Map. Filters to trt_cp...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CLUE_search_compounds(
    operation: str,
    pert_iname: Optional[str] = None,
    moa: Optional[str] = None,
    limit: Optional[int] = 50,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search chemical compounds (small molecule drugs) in the L1000 Connectivity Map. Filters to trt_cp...

    Parameters
    ----------
    operation : str
        Operation type
    pert_iname : str
        Compound name search (partial match). E.g., 'imatinib', 'vorinostat'
    moa : str
        Mechanism of action search. E.g., 'HDAC inhibitor', 'kinase inhibitor'
    limit : int
        Maximum number of results
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

    return get_shared_client().run_one_function(
        {
            "name": "CLUE_search_compounds",
            "arguments": {
                "operation": operation,
                "pert_iname": pert_iname,
                "moa": moa,
                "limit": limit,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CLUE_search_compounds"]
