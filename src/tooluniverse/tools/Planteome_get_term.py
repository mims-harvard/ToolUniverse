"""
Planteome_get_term

Get a single Planteome ontology term by its accession ID (from Planteome_search_terms or Planteom...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Planteome_get_term(
    term_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get a single Planteome ontology term by its accession ID (from Planteome_search_terms or Planteom...

    Parameters
    ----------
    term_id : str
        Ontology term accession, e.g. 'GO:0009555' or 'PO:0025281'.
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
    _args = {k: v for k, v in {"term_id": term_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "Planteome_get_term",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Planteome_get_term"]
