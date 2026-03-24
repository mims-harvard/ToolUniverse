"""
Progenetix_list_cohorts

List available cohorts in the Progenetix cancer CNV database.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Progenetix_list_cohorts(
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List available cohorts in the Progenetix database.

    Parameters
    ----------
    limit : int, optional
        Maximum number of cohorts to return (default 10).
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
    _args = {k: v for k, v in {"limit": limit}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "Progenetix_list_cohorts",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Progenetix_list_cohorts"]
