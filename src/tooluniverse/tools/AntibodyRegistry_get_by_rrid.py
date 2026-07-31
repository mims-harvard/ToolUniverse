"""
AntibodyRegistry_get_by_rrid

Resolve a research-antibody RRID (e.g. 'AB_2298772', 'RRID:AB_2298772', or the bare numeric id) t...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def AntibodyRegistry_get_by_rrid(
    rrid: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Resolve a research-antibody RRID (e.g. 'AB_2298772', 'RRID:AB_2298772', or the bare numeric id) t...

    Parameters
    ----------
    rrid : str
        Antibody RRID, e.g. 'AB_2298772', 'RRID:AB_2298772', or a bare numeric id lik...
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
    _args = {k: v for k, v in {"rrid": rrid}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "AntibodyRegistry_get_by_rrid",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["AntibodyRegistry_get_by_rrid"]
