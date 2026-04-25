"""
OmicsDI_get_dataset

Get detailed information about a specific omics dataset in OmicsDI by accession number and source...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OmicsDI_get_dataset(
    accession: str,
    database: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed information about a specific omics dataset in OmicsDI by accession number and source...

    Parameters
    ----------
    accession : str
        Dataset accession number (e.g., 'MTBLS1355', 'E-GEOD-100000', 'PXD000001')
    database : str
        Source database name (e.g., 'metabolights_dataset', 'arrayexpress-repository'...
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
    _args = {k: v for k, v in {
        "accession": accession,
                "database": database
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "OmicsDI_get_dataset",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["OmicsDI_get_dataset"]
