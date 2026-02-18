"""
OMIM_get_clinical_synopsis

Get clinical synopsis (phenotype features) for an OMIM phenotype entry. Returns structured clinic...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OMIM_get_clinical_synopsis(
    operation: str,
    mim_number: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get clinical synopsis (phenotype features) for an OMIM phenotype entry. Returns structured clinic...

    Parameters
    ----------
    operation : str
        Operation type (fixed: get_clinical_synopsis)
    mim_number : str
        OMIM MIM number for phenotype (e.g., 219700 for cystic fibrosis)
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
            "name": "OMIM_get_clinical_synopsis",
            "arguments": {"operation": operation, "mim_number": mim_number},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OMIM_get_clinical_synopsis"]
