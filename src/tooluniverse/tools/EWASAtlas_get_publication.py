"""
EWASAtlas_get_publication

Get the epigenome-wide association studies (EWAS) that EWAS Atlas curated from one publication, b...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EWASAtlas_get_publication(
    pmid: str,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get the epigenome-wide association studies (EWAS) that EWAS Atlas curated from one publication, b...

    Parameters
    ----------
    pmid : str
        PubMed ID, e.g. '29535343'.
    limit : int
        Max associations per study to return, 1-1000. Default 50.
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
    _args = {k: v for k, v in {"pmid": pmid, "limit": limit}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "EWASAtlas_get_publication",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EWASAtlas_get_publication"]
