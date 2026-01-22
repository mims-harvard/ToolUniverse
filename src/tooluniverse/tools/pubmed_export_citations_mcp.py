"""
pubmed_export_citations_mcp

Export citations in RIS, BibTeX, CSV, or MEDLINE format.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def pubmed_export_citations_mcp(
    pmids: str,
    format: Optional[str] = "ris",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Export citations in RIS, BibTeX, CSV, or MEDLINE format.

    Parameters
    ----------
    pmids : str
        Comma-separated PMIDs (max 50)
    format : str

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
            "name": "pubmed_export_citations_mcp",
            "arguments": {"pmids": pmids, "format": format},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["pubmed_export_citations_mcp"]
