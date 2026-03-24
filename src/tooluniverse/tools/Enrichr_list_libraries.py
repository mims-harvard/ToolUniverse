"""
Enrichr_list_libraries

List all available Enrichr gene set libraries with statistics. Enrichr has 225+ libraries coverin...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Enrichr_list_libraries(
    operation: Optional[str] = None,
    category: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    List all available Enrichr gene set libraries with statistics. Enrichr has 225+ libraries coverin...

    Parameters
    ----------
    operation : str
        Operation type (fixed: list_libraries)
    category : str
        Optional keyword to filter libraries (e.g., 'GO', 'KEGG', 'Reactome', 'diseas...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {"operation": operation, "category": category}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Enrichr_list_libraries",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Enrichr_list_libraries"]
