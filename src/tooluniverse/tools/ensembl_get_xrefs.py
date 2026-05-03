"""
ensembl_get_xrefs

Get cross-references (external database IDs) for an Ensembl gene, transcript, or protein. Returns...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ensembl_get_xrefs(
    id: str,
    external_db: Optional[str] = None,
    object_type: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get cross-references (external database IDs) for an Ensembl gene, transcript, or protein. Returns...

    Parameters
    ----------
    id : str
        Ensembl ID (gene, transcript, or protein ID, e.g., 'ENSG00000139618', 'ENST00...
    external_db : str
        Filter by external database name (optional, e.g., 'UniProt', 'RefSeq', 'HGNC')
    object_type : str
        Object type filter (optional, e.g., 'gene', 'transcript', 'translation')
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
        for k, v in {
            "id": id,
            "external_db": external_db,
            "object_type": object_type,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ensembl_get_xrefs",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ensembl_get_xrefs"]
