"""
EPMC_get_article_organisms

Get organisms mentioned in a biomedical article, identified by text mining from Europe PMC. Retur...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EPMC_get_article_organisms(
    pmid: Optional[str] = None,
    pmcid: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get organisms mentioned in a biomedical article, identified by text mining from Europe PMC. Retur...

    Parameters
    ----------
    pmid : str
        PubMed ID (e.g., '33332779').
    pmcid : str
        PubMed Central ID (e.g., 'PMC7781101'). Alternative to pmid.
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
    _args = {k: v for k, v in {"pmid": pmid, "pmcid": pmcid}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "EPMC_get_article_organisms",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EPMC_get_article_organisms"]
