"""
Nextstrain_get_dataset

Get metadata and phylogenetic summary for a Nextstrain pathogen dataset. Returns title, last upda...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Nextstrain_get_dataset(
    dataset: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get metadata and phylogenetic summary for a Nextstrain pathogen dataset. Returns title, last upda...

    Parameters
    ----------
    dataset : str
        Nextstrain dataset path. Examples: 'zika', 'ebola', 'flu/seasonal/h3n2/ha/2y'...
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
    _args = {k: v for k, v in {"dataset": dataset}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "Nextstrain_get_dataset",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Nextstrain_get_dataset"]
