"""
NCBI_SRA_locate_run_files

Resolve the current, verified cloud download location(s) plus authoritative file size and md5 che...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NCBI_SRA_locate_run_files(
    accessions: list[str] | str,
    operation: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Resolve the current, verified cloud download location(s) plus authoritative file size and md5 che...

    Parameters
    ----------
    operation : str
        Operation type (fixed: locate_run_files)
    accessions : list[str] | str
        SRA run accession(s) (e.g., 'SRR390728', 'ERR000001', 'DRR000001'). Single ac...
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
        for k, v in {"operation": operation, "accessions": accessions}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "NCBI_SRA_locate_run_files",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NCBI_SRA_locate_run_files"]
