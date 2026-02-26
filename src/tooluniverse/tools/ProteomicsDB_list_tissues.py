"""
ProteomicsDB_list_tissues

List all available tissues, cell lines, and body fluids in ProteomicsDB with their BTO ontology I...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ProteomicsDB_list_tissues(
    operation: str,
    tissue_category: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    List all available tissues, cell lines, and body fluids in ProteomicsDB with their BTO ontology I...

    Parameters
    ----------
    operation : str
        Operation type
    tissue_category : str
        Filter by biological source category. Optional - omit to list all categories.
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    return get_shared_client().run_one_function(
        {
            "name": "ProteomicsDB_list_tissues",
            "arguments": {"operation": operation, "tissue_category": tissue_category},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ProteomicsDB_list_tissues"]
