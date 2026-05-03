"""
HGNC_fetch_gene_by_id

Fetch gene information from HGNC by HGNC ID. Useful when you have a specific HGNC identifier and ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def HGNC_fetch_gene_by_id(
    hgnc_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Fetch gene information from HGNC by HGNC ID. Useful when you have a specific HGNC identifier and ...

    Parameters
    ----------
    hgnc_id : str
        HGNC identifier, with or without 'HGNC:' prefix. Examples: 'HGNC:11998' (TP53...
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
    _args = {k: v for k, v in {"hgnc_id": hgnc_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "HGNC_fetch_gene_by_id",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["HGNC_fetch_gene_by_id"]
