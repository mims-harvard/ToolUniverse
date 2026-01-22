"""
pubmed_get_full_text_mcp

Get fulltext from Europe PMC. Supports PMID, PMC ID, or DOI input. Auto-tries multiple sources.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def pubmed_get_full_text_mcp(
    pmcid: Optional[str] = None,
    pmid: Optional[str] = None,
    doi: Optional[str] = None,
    sections: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get fulltext from Europe PMC. Supports PMID, PMC ID, or DOI input. Auto-tries multiple sources.

    Parameters
    ----------
    pmcid : str
        PubMed Central ID
    pmid : str
        PubMed ID
    doi : str
        Digital Object Identifier
    sections : str
        Comma-separated sections to retrieve
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

    return get_shared_client().run_one_function(
        {
            "name": "pubmed_get_full_text_mcp",
            "arguments": {
                "pmcid": pmcid,
                "pmid": pmid,
                "doi": doi,
                "sections": sections,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["pubmed_get_full_text_mcp"]
