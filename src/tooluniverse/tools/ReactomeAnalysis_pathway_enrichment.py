"""
ReactomeAnalysis_pathway_enrichment

Perform pathway overrepresentation (enrichment) analysis using the Reactome Analysis Service. Sub...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ReactomeAnalysis_pathway_enrichment(
    identifiers: str,
    page_size: Optional[int | Any] = None,
    include_disease: Optional[bool | Any] = None,
    projection: Optional[bool | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Perform pathway overrepresentation (enrichment) analysis using the Reactome Analysis Service. Sub...

    Parameters
    ----------
    identifiers : str
        Newline-separated list of gene/protein identifiers. Supports gene symbols (TP...
    page_size : int | Any
        Number of pathways to return (default 20, max 50).
    include_disease : bool | Any
        Include disease pathways in results (default true).
    projection : bool | Any
        Project identifiers to human Reactome pathways for cross-species analysis (de...
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
            "identifiers": identifiers,
            "page_size": page_size,
            "include_disease": include_disease,
            "projection": projection,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ReactomeAnalysis_pathway_enrichment",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ReactomeAnalysis_pathway_enrichment"]
