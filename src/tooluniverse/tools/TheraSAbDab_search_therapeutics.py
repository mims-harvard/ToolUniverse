"""
TheraSAbDab_search_therapeutics

Search therapeutic antibodies by name in Thera-SAbDab. Returns WHO INN name, target antigen, form...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def TheraSAbDab_search_therapeutics(
    query: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search therapeutic antibodies by name in Thera-SAbDab. Returns WHO INN name, target antigen, form...

    Parameters
    ----------
    query : str
        Search query - antibody name (e.g., 'trastuzumab', 'pembrolizumab', 'rituximab')
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
    _args = {k: v for k, v in {"query": query}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "TheraSAbDab_search_therapeutics",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["TheraSAbDab_search_therapeutics"]
