"""
Bioregistry_resolve_reference

Resolve a compact identifier (prefix:id) to provider URLs across 2600+ biological databases. Give...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Bioregistry_resolve_reference(
    prefix: str,
    identifier: str,
    operation: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Resolve a compact identifier (prefix:id) to provider URLs across 2600+ biological databases. Give...

    Parameters
    ----------
    operation : str
        Operation type (fixed: resolve_reference)
    prefix : str
        Database prefix (e.g., 'uniprot', 'chebi', 'go', 'pubmed', 'ensembl', 'hgnc')
    identifier : str
        Database identifier (e.g., 'P04637' for UniProt, '17234' for ChEBI, '0006915'...
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

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "operation": operation,
            "prefix": prefix,
            "identifier": identifier,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Bioregistry_resolve_reference",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Bioregistry_resolve_reference"]
