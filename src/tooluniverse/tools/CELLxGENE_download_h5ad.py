"""
CELLxGENE_download_h5ad

Download original H5AD (HDF5-based AnnData) files from CELLxGENE datasets or get their URIs. Acce...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CELLxGENE_download_h5ad(
    operation: str,
    dataset_id: str,
    output_path: Optional[str] = None,
    census_version: Optional[str] = "stable",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Optional[dict[str, Any]]:
    """
    Download original H5AD (HDF5-based AnnData) files from CELLxGENE datasets or get their URIs. Acce...

    Parameters
    ----------
    operation : str
        Operation type
    dataset_id : str
        CELLxGENE dataset identifier (required)
    output_path : str
        Local path to save H5AD file (omit to get URI only)
    census_version : str
        Census version to query. 'stable' (recommended, Long-Term Support release), '...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    Optional[dict[str, Any]]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "operation": operation,
            "dataset_id": dataset_id,
            "output_path": output_path,
            "census_version": census_version,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "CELLxGENE_download_h5ad",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CELLxGENE_download_h5ad"]
