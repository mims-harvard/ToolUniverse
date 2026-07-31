"""
SGD_get_regulation

Get the transcriptional regulation network for a yeast gene from SGD: curated regulator->target r...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SGD_get_regulation(
    sgd_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the transcriptional regulation network for a yeast gene from SGD: curated regulator->target r...

    Parameters
    ----------
    sgd_id : str
        SGD locus identifier. Examples: 'S000000364' (CDC28), 'S000000259' (GAL4).
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
    _args = {k: v for k, v in {"sgd_id": sgd_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "SGD_get_regulation",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SGD_get_regulation"]
