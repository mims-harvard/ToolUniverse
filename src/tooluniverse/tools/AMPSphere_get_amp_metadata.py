"""
AMPSphere_get_amp_metadata

Page through the samples one AMPSphere peptide was observed in: per sample, the GMSC gene accessi...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def AMPSphere_get_amp_metadata(
    accession: str,
    page: Optional[int] = 0,
    page_size: Optional[int] = 20,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Page through the samples one AMPSphere peptide was observed in: per sample, the GMSC gene accessi...

    Parameters
    ----------
    accession : str
        AMPSphere AMP accession. Example: 'AMP10.000_000'.
    page : int
        Zero-based page number.
    page_size : int
        Rows per page (upstream default 20).
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
            "accession": accession,
            "page": page,
            "page_size": page_size,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "AMPSphere_get_amp_metadata",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["AMPSphere_get_amp_metadata"]
