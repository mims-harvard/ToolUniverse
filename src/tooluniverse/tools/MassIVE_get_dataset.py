"""
MassIVE_get_dataset

Get detailed information about a specific MassIVE proteomics dataset by its accession number (MSV...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MassIVE_get_dataset(
    accession: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed information about a specific MassIVE proteomics dataset by its accession number (MSV...

    Parameters
    ----------
    accession : str
        MassIVE dataset accession (e.g., 'MSV000079514') or ProteomeXchange accession...
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
    _args = {k: v for k, v in {"accession": accession}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "MassIVE_get_dataset",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MassIVE_get_dataset"]
