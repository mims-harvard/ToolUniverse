"""
Carbon_A_get_benchmark_genome

Get the files and assembly details of one genome in the Carbon-A evaluation collection. Returns e...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Carbon_A_get_benchmark_genome(
    accession: str,
    include_sequence_report: Optional[bool] = True,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get the files and assembly details of one genome in the Carbon-A evaluation collection. Returns e...

    Parameters
    ----------
    accession : str
        NCBI assembly accession of a genome in the collection, for example 'GCF_00014...
    include_sequence_report : bool
        Include the per-molecule sequence report. Default true.
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
            "include_sequence_report": include_sequence_report,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Carbon_A_get_benchmark_genome",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Carbon_A_get_benchmark_genome"]
