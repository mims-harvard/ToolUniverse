"""
NCBI_SRA_get_download_urls

Get FTP and cloud storage URLs for downloading FASTQ sequencing data from SRA runs. Returns multi...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NCBI_SRA_get_download_urls(
    operation: str,
    accessions: list[str] | str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get FTP and cloud storage URLs for downloading FASTQ sequencing data from SRA runs. Returns multi...

    Parameters
    ----------
    operation : str
        Operation type (fixed: get_download_urls)
    accessions : list[str] | str
        SRA run accession(s) (e.g., 'SRR000001', 'ERR000001', 'DRR000001'). Can be si...
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

    return get_shared_client().run_one_function(
        {
            "name": "NCBI_SRA_get_download_urls",
            "arguments": {"operation": operation, "accessions": accessions},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NCBI_SRA_get_download_urls"]
