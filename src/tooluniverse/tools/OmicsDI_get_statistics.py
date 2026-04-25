"""
OmicsDI_get_statistics

Get statistics about the OmicsDI omics data repositories. Returns counts of datasets across diffe...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OmicsDI_get_statistics(
    stat_type: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get statistics about the OmicsDI omics data repositories. Returns counts of datasets across diffe...

    Parameters
    ----------
    stat_type : str
        Type of statistics: 'domains' (list all data sources), 'organisms' (count by ...
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
        "stat_type": stat_type
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "OmicsDI_get_statistics",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["OmicsDI_get_statistics"]
