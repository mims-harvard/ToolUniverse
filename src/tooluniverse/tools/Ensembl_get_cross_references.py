"""
Ensembl_get_cross_references

Get all external database cross-references for an Ensembl stable identifier. Returns linked recor...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Ensembl_get_cross_references(
    ensembl_id: str,
    external_db: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get all external database cross-references for an Ensembl stable identifier. Returns linked recor...

    Parameters
    ----------
    ensembl_id : str
        Ensembl stable identifier. Can be gene (ENSG*), transcript (ENST*), or transl...
    external_db : str | Any
        Optional: filter by external database name. Examples: 'HGNC', 'EntrezGene', '...
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
        for k, v in {"ensembl_id": ensembl_id, "external_db": external_db}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Ensembl_get_cross_references",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Ensembl_get_cross_references"]
