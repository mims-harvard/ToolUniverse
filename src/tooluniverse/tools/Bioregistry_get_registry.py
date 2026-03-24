"""
Bioregistry_get_registry

Get metadata for a biological database/ontology by its Bioregistry prefix. Returns name, descript...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Bioregistry_get_registry(
    prefix: str,
    operation: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get metadata for a biological database/ontology by its Bioregistry prefix. Returns name, descript...

    Parameters
    ----------
    operation : str
        Operation type (fixed: get_registry)
    prefix : str
        Bioregistry prefix (e.g., 'uniprot', 'chebi', 'go', 'pdb', 'ensembl', 'hgnc',...
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
        for k, v in {"operation": operation, "prefix": prefix}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Bioregistry_get_registry",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Bioregistry_get_registry"]
