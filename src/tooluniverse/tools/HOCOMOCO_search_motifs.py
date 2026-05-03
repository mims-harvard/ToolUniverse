"""
HOCOMOCO_search_motifs

Search HOCOMOCO v14 for transcription factor binding motifs by gene or protein name. Returns moti...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def HOCOMOCO_search_motifs(
    query: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search HOCOMOCO v14 for transcription factor binding motifs by gene or protein name. Returns moti...

    Parameters
    ----------
    query : str
        Gene symbol or protein name to search for TF binding motifs. Examples: 'TP53'...
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

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {"query": query}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "HOCOMOCO_search_motifs",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["HOCOMOCO_search_motifs"]
