"""
RxClass_get_drug_classes

Get drug classification from NLM RxClass for a drug name or RXCUI.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def RxClass_get_drug_classes(
    drug_name: Optional[str] = None,
    rxcui: Optional[str] = None,
    rela_source: Optional[str] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get drug classification from NLM RxClass for a drug name or RXCUI.

    Parameters
    ----------
    drug_name : str, optional
        Drug name to classify (e.g., 'metformin', 'aspirin').
    rxcui : str, optional
        RxNorm RXCUI identifier (alternative to drug_name).
    rela_source : str, optional
        Classification source: 'ATC' (default), 'FDASPL', 'MESH', 'VA', 'DAILYMED', 'ALL'.
    limit : int, optional
        Maximum results to return (default 20).
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
    _args = {
        k: v
        for k, v in {
            "drug_name": drug_name,
            "rxcui": rxcui,
            "rela_source": rela_source,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "RxClass_get_drug_classes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["RxClass_get_drug_classes"]
