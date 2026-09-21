"""
DbGaP_search_studies

Search dbGaP (NCBI's controlled-access US genotype-phenotype archive, the American counterpart to...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DbGaP_search_studies(
    query: str,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search dbGaP (NCBI's controlled-access US genotype-phenotype archive, the American counterpart to...

    Parameters
    ----------
    query : str
        Study title keyword, e.g. 'diabetes', 'autism'.
    limit : int
        Max studies to return, 1-100. Default 25.
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
    _args = {k: v for k, v in {"query": query, "limit": limit}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "DbGaP_search_studies",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DbGaP_search_studies"]
