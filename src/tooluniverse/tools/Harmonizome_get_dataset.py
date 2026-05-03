"""
Harmonizome_get_dataset

Get detailed information about a specific dataset integrated in Harmonizome (Ma'ayan Lab). Return...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Harmonizome_get_dataset(
    dataset_name: str,
    gene_set_limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed information about a specific dataset integrated in Harmonizome (Ma'ayan Lab). Return...

    Parameters
    ----------
    dataset_name : str
        Exact dataset name from Harmonizome. Examples: 'CTD Gene-Disease Associations...
    gene_set_limit : int
        Maximum number of gene set names to return (default: 50).
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
