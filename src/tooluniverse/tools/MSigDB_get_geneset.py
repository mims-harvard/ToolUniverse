"""
MSigDB_get_geneset

Retrieve a specific gene set from MSigDB (Molecular Signatures Database) by its exact name. MSigD...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MSigDB_get_geneset(
    geneSetName: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve a specific gene set from MSigDB (Molecular Signatures Database) by its exact name. MSigD...

    Parameters
    ----------
    geneSetName : str
        Exact MSigDB gene set name (case-sensitive). Examples: 'HALLMARK_APOPTOSIS', ...
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
    _args = {k: v for k, v in {"geneSetName": geneSetName}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "MSigDB_get_geneset",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MSigDB_get_geneset"]
