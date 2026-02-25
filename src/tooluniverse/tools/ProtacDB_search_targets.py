"""
ProtacDB_search_targets

Search PROTAC target proteins in PROTAC-DB 3.0. Returns target protein names (short and long). Ov...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ProtacDB_search_targets(
    operation: str,
    target_name: Optional[str | Any] = None,
    uniprot_id: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search PROTAC target proteins in PROTAC-DB 3.0. Returns target protein names (short and long). Ov...

    Parameters
    ----------
    operation : str
        Operation type
    target_name : str | Any
        Target protein name or gene symbol (e.g., 'BRD4', 'KRAS'). Returns all target...
    uniprot_id : str | Any
        UniProt accession ID (e.g., 'O60885' for BRD4). Mutually exclusive with targe...
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
            "name": "ProtacDB_search_targets",
            "arguments": {
                "operation": operation,
                "target_name": target_name,
                "uniprot_id": uniprot_id,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ProtacDB_search_targets"]
