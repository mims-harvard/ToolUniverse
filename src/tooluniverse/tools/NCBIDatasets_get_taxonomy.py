"""
NCBIDatasets_get_taxonomy

Get detailed taxonomy information from NCBI by taxonomy ID. Returns organism name, rank, full lin...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NCBIDatasets_get_taxonomy(
    tax_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed taxonomy information from NCBI by taxonomy ID. Returns organism name, rank, full lin...

    Parameters
    ----------
    tax_id : str
        NCBI Taxonomy ID (numeric). Examples: '9606' (Homo sapiens), '10090' (Mus mus...
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
    _args = {k: v for k, v in {"tax_id": tax_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "NCBIDatasets_get_taxonomy",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NCBIDatasets_get_taxonomy"]
