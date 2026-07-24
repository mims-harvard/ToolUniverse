"""
PubTator3_GetEntityRelations

Query the NCBI PubTator3 relation knowledge graph for a normalized biomedical entity and return R...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PubTator3_GetEntityRelations(
    e1: str,
    type_: Optional[str] = None,
    e2: Optional[str] = None,
    limit: Optional[int] = 50,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Query the NCBI PubTator3 relation knowledge graph for a normalized biomedical entity and return R...

    Parameters
    ----------
    e1 : str
        Primary normalized PubTator entity in @TYPE_Name format. Examples: '@GENE_BRA...
    type_ : str
        Optional relation type filter to restrict edges. Examples: 'treat', 'cause', ...
    e2 : str
        Optional second normalized PubTator entity (@TYPE_Name) to query a specific p...
    limit : int
        Maximum number of top-ranked relation edges to return (client-side truncation...
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
        for k, v in {"e1": e1, "type": type_, "e2": e2, "limit": limit}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PubTator3_GetEntityRelations",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PubTator3_GetEntityRelations"]
