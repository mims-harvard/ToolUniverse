"""
GOAPI_get_term

Get detailed information about a Gene Ontology (GO) term by its GO ID. Returns the term label, fu...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GOAPI_get_term(
    go_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed information about a Gene Ontology (GO) term by its GO ID. Returns the term label, fu...

    Parameters
    ----------
    go_id : str
        Gene Ontology term ID. Format: GO:NNNNNNN. Examples: 'GO:0006915' (apoptotic ...
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
    _args = {k: v for k, v in {"go_id": go_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "GOAPI_get_term",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GOAPI_get_term"]
