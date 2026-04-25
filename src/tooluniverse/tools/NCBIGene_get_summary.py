"""
NCBIGene_get_summary

Get a detailed gene summary from NCBI Gene by Entrez Gene ID using the E-utilities ESummary API. ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NCBIGene_get_summary(
    id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get a detailed gene summary from NCBI Gene by Entrez Gene ID using the E-utilities ESummary API. ...

    Parameters
    ----------
    id : str
        NCBI Gene ID (Entrez Gene ID). Can be a single ID or comma-separated list. Ex...
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
        "id": id
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "NCBIGene_get_summary",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["NCBIGene_get_summary"]
