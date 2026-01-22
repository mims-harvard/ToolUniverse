"""
pubmed_get_text_mined_terms_mcp

Get text-mined entities (genes, diseases, chemicals) from Europe PMC annotations.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def pubmed_get_text_mined_terms_mcp(
    pmcid: Optional[str] = None,
    pmid: Optional[str] = None,
    entity_types: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get text-mined entities (genes, diseases, chemicals) from Europe PMC annotations.

    Parameters
    ----------
    pmcid : str

    pmid : str

    entity_types : str
        Filter by entity types (genes,diseases,chemicals)
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
            "name": "pubmed_get_text_mined_terms_mcp",
            "arguments": {"pmcid": pmcid, "pmid": pmid, "entity_types": entity_types},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["pubmed_get_text_mined_terms_mcp"]
