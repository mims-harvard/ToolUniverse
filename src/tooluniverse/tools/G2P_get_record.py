"""
G2P_get_record

Get detailed Gene2Phenotype (G2P) record for a specific gene-disease association by its stable ID...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def G2P_get_record(
    stable_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed Gene2Phenotype (G2P) record for a specific gene-disease association by its stable ID...

    Parameters
    ----------
    stable_id : str
        G2P stable identifier (e.g., 'G2P01796', 'G2P00119', 'G2P00979'). Get IDs fro...
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

    return get_shared_client().run_one_function(
        {"name": "G2P_get_record", "arguments": {"stable_id": stable_id}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["G2P_get_record"]
