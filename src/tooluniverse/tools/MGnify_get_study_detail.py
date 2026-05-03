"""
MGnify_get_study_detail

Get detailed information about a specific MGnify metagenomics study. Returns study name, abstract...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MGnify_get_study_detail(
    study_accession: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed information about a specific MGnify metagenomics study. Returns study name, abstract...

    Parameters
    ----------
    study_accession : str
        MGnify study accession. Examples: 'MGYS00002008', 'MGYS00005292'.
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
        k: v for k, v in {"study_accession": study_accession}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MGnify_get_study_detail",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MGnify_get_study_detail"]
