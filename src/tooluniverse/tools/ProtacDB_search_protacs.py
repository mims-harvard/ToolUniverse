"""
ProtacDB_search_protacs

Search PROTAC-DB 3.0 for PROTAC (Proteolysis Targeting Chimera) compounds. Filter by target prote...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ProtacDB_search_protacs(
    operation: str,
    target: Optional[str | Any] = None,
    e3_ligase: Optional[str | Any] = None,
    max_results: Optional[int] = 50,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search PROTAC-DB 3.0 for PROTAC (Proteolysis Targeting Chimera) compounds. Filter by target prote...

    Parameters
    ----------
    operation : str
        Operation type
    target : str | Any
        Target protein name or gene symbol (e.g., 'BRD4', 'KRAS', 'AR', 'BCL2'). At l...
    e3_ligase : str | Any
        E3 ubiquitin ligase (e.g., 'CRBN', 'VHL', 'MDM2', 'XIAP'). At least one of ta...
    max_results : int
        Maximum number of compounds to return (default 50, max 100)
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
            "name": "ProtacDB_search_protacs",
            "arguments": {
                "operation": operation,
                "target": target,
                "e3_ligase": e3_ligase,
                "max_results": max_results,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ProtacDB_search_protacs"]
