"""
EnsemblArchive_batch_lookup

Batch lookup version histories for multiple Ensembl stable IDs. Returns current status, release, ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EnsemblArchive_batch_lookup(
    ensembl_ids: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Batch lookup version histories for multiple Ensembl stable IDs. Returns current status, release, ...

    Parameters
    ----------
    ensembl_ids : str
        Comma-separated Ensembl stable IDs (max 50). Example: 'ENSG00000141510,ENSG00...
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

    return get_shared_client().run_one_function(
        {
            "name": "EnsemblArchive_batch_lookup",
            "arguments": {"ensembl_ids": ensembl_ids},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EnsemblArchive_batch_lookup"]
