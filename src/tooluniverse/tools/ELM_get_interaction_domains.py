"""
ELM_get_interaction_domains

Get the ELM motif-to-interaction-domain mapping: for each Short Linear Motif (SLiM) class, the pr...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ELM_get_interaction_domains(
    operation: str,
    elm_identifier: Optional[str] = None,
    query: Optional[str] = None,
    max_results: Optional[int] = 100,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the ELM motif-to-interaction-domain mapping: for each Short Linear Motif (SLiM) class, the pr...

    Parameters
    ----------
    operation : str
        Operation type
    elm_identifier : str
        Filter to a single ELM class identifier (e.g., 'CLV_NRD_NRD_1', 'LIG_SH3_1')....
    query : str
        Free-text filter matched against ELM identifier, Pfam accession, domain name,...
    max_results : int
        Maximum mappings to return (default: 100, max: 500 covers all 427 mappings)
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
            "operation": operation,
            "elm_identifier": elm_identifier,
            "query": query,
            "max_results": max_results,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ELM_get_interaction_domains",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ELM_get_interaction_domains"]
