"""
ReactomeAnalysis_token_result

Retrieve previously computed Reactome pathway analysis results using an analysis token. Tokens ar...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ReactomeAnalysis_token_result(
    token: str,
    page_size: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve previously computed Reactome pathway analysis results using an analysis token. Tokens ar...

    Parameters
    ----------
    token : str
        Analysis token from a previous ReactomeAnalysis_pathway_enrichment or Reactom...
    page_size : int | Any
        Number of pathways per page (default 20, max 50).
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
        for k, v in {"token": token, "page_size": page_size}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ReactomeAnalysis_token_result",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ReactomeAnalysis_token_result"]
