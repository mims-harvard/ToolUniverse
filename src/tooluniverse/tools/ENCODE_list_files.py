"""
ENCODE_list_files

List ENCODE data files with filters by file format, output type, or assay. Returns file metadata ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ENCODE_list_files(
    file_type: Optional[str] = None,
    assay_title: Optional[str] = None,
    limit: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    List ENCODE data files with filters by file format, output type, or assay. Returns file metadata ...

    Parameters
    ----------
    file_type : str
        File format filter (e.g., 'fastq', 'bam', 'bigWig', 'bed'). Common formats: f...
    assay_title : str
        Assay filter (e.g., 'ChIP-seq', 'RNA-seq'). Filters files by the experimental...
    limit : int
        Maximum number of results to return (1–100).
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
            "file_type": file_type,
            "assay_title": assay_title,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ENCODE_list_files",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ENCODE_list_files"]
