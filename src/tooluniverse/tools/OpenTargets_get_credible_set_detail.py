"""
OpenTargets_get_credible_set_detail

Get detailed information about a specific GWAS credible set (fine-mapped locus) from Open Targets...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenTargets_get_credible_set_detail(
    studyLocusId: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed information about a specific GWAS credible set (fine-mapped locus) from Open Targets...

    Parameters
    ----------
    studyLocusId : str
        Credible set identifier (studyLocusId), a 32-character hash (e.g., 'b758d8fb1...
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
    _args = {k: v for k, v in {"studyLocusId": studyLocusId}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "OpenTargets_get_credible_set_detail",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenTargets_get_credible_set_detail"]
