"""
RxClass_get_drug_classes

Get NLM RxClass classifications for a drug name or RXCUI across ATC, EPC, MoA, VA and other sourc...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def RxClass_get_drug_classes(
    drug_name: Optional[str] = None,
    rxcui: Optional[str] = None,
    rela_source: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get NLM RxClass classifications for a drug name or RXCUI across ATC, EPC, MoA, VA and other sourc...

    Parameters
    ----------
    drug_name : str
        Drug name to classify. Examples: 'metformin', 'aspirin', 'ibuprofen', 'metopr...
    rxcui : str
        RxNorm RXCUI identifier (alternative to drug_name). Examples: '6809' (metform...
    rela_source : str
        Classification source. Options: 'ATC' (WHO Anatomical Therapeutic Chemical, d...
    limit : int
        Maximum results to return (default 20).
    offset : int
        Zero-based offset in the complete deduplicated drug-class relation list. Cont...
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
            "drug_name": drug_name,
            "rxcui": rxcui,
            "rela_source": rela_source,
            "limit": limit,
            "offset": offset,
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
