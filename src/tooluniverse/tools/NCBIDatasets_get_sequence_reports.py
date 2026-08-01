"""
NCBIDatasets_get_sequence_reports

Get a page of per-sequence reports for a genome assembly via the NCBI Datasets v2 API.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NCBIDatasets_get_sequence_reports(
    accession: str,
    page_size: Optional[int] = None,
    page_token: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get a page of chromosome, plasmid, or scaffold reports for an assembly.

    Parameters
    ----------
    accession : str
        Assembly accession, e.g. 'GCF_000005845.2'.
    page_size : int, optional
        Maximum records in this page (default 100, maximum 1000).
    page_token : str, optional
        Opaque next_page_token from a previous call. Omit for the first page.
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
        for k, v in {
            "accession": accession,
            "page_size": page_size,
            "page_token": page_token,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "NCBIDatasets_get_sequence_reports",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NCBIDatasets_get_sequence_reports"]
