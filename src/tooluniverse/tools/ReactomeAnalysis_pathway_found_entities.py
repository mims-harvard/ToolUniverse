"""
ReactomeAnalysis_pathway_found_entities

Per-pathway found-entities drill-down: for an analysis token and a specific HIT pathway, list exa...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ReactomeAnalysis_pathway_found_entities(
    token: str,
    pathway: str,
    resource: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Per-pathway found-entities drill-down: for an analysis token and a specific HIT pathway, list exa...

    Parameters
    ----------
    token : str
        Analysis token from a previous ReactomeAnalysis_pathway_enrichment or Reactom...
    pathway : str
        Reactome pathway stable id of a hit pathway from the analysis result (e.g. 'R...
    resource : str
        Resource to map entities against (default 'TOTAL'). Other options: 'UNIPROT',...
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
        for k, v in {"token": token, "pathway": pathway, "resource": resource}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ReactomeAnalysis_pathway_found_entities",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ReactomeAnalysis_pathway_found_entities"]
