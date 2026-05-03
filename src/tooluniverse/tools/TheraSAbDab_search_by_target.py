"""
TheraSAbDab_search_by_target

Find therapeutic antibodies targeting a specific antigen. Returns all clinical/approved antibodie...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def TheraSAbDab_search_by_target(
    target: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Find therapeutic antibodies targeting a specific antigen. Returns all clinical/approved antibodie...

    Parameters
    ----------
    target : str
        Target antigen name (e.g., 'PD-1', 'HER2', 'CD20', 'TNF-alpha', 'VEGF')
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
    _args = {k: v for k, v in {"target": target}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "TheraSAbDab_search_by_target",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["TheraSAbDab_search_by_target"]
