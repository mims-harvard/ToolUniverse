"""
PubTator3_GetEntityRelations

Query the NCBI PubTator3 relation graph for a normalized biomedical entity. PubTator returns the ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PubTator3_GetEntityRelations(
    e1: str,
    type_: Optional[str] = None,
    e2: Optional[str] = None,
    limit: Optional[int] = 50,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Query the NCBI PubTator3 relation graph for a normalized biomedical entity. PubTator returns the ...

    Parameters
    ----------
    e1 : str
        Primary normalized PubTator entity in @TYPE_Name format. Examples: '@GENE_BRA...
    type_ : str
        Optional relation type filter to restrict edges. Examples: 'treat', 'cause', ...
    e2 : str
        Optional second normalized PubTator entity (@TYPE_Name) to query a specific p...
    limit : int
        Number of ranked relation edges in this client-side page (default 50).
    offset : int
        Zero-based ranked-edge offset. Continue with metadata.next_offset while metad...
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
            "e1": e1,
            "type": type_,
            "e2": e2,
            "limit": limit,
            "offset": offset,
        }.items()
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
