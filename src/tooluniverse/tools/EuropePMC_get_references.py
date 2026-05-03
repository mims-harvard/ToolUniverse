"""
EuropePMC_get_references

Get references (bibliography) for an article from Europe PMC. References are articles cited by th...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EuropePMC_get_references(
    article_id: str,
    source: Optional[str] = "MED",
    page_size: Optional[int] = 25,
    page: Optional[int] = 1,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get references (bibliography) for an article from Europe PMC. References are articles cited by th...

    Parameters
    ----------
    source : str
        Source database (e.g., 'MED' for PubMed, 'PMC' for PMC). Usually 'MED' for mo...
    article_id : str
        Article ID from the source database (e.g., PMID for MED source)
    page_size : int
        Number of references to retrieve (default: 25, max: 1000)
    page : int
        Page number for pagination (default: 1)
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
            "source": source,
            "article_id": article_id,
            "page_size": page_size,
            "page": page,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EuropePMC_get_references",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EuropePMC_get_references"]
