"""
Harmonizome_get_dataset

Get Harmonizome dataset metadata plus a recoverable page of its gene-set catalog. Large datasets ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Harmonizome_get_dataset(
    dataset_name: str,
    gene_set_limit: Optional[int] = None,
    gene_set_offset: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get Harmonizome dataset metadata plus a recoverable page of its gene-set catalog. Large datasets ...

    Parameters
    ----------
    dataset_name : str
        Exact dataset name from Harmonizome. Examples: 'CTD Gene-Disease Associations...
    gene_set_limit : int
        Gene set names per page (default 50, max 1000).
    gene_set_offset : int
        Zero-based offset into the complete gene-set catalog. Continue with metadata....
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
            "dataset_name": dataset_name,
            "gene_set_limit": gene_set_limit,
            "gene_set_offset": gene_set_offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Harmonizome_get_dataset",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Harmonizome_get_dataset"]
