"""
OncoKB_get_cancer_genes

Get list of all cancer genes curated in OncoKB. Returns genes classified as oncogenes and/or tumo...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OncoKB_get_cancer_genes(
    operation: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get list of all cancer genes curated in OncoKB. Returns genes classified as oncogenes and/or tumo...

    Parameters
    ----------
    operation : str
        Operation type (fixed: get_cancer_genes)
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
    _args = {k: v for k, v in {"operation": operation}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "OncoKB_get_cancer_genes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OncoKB_get_cancer_genes"]
