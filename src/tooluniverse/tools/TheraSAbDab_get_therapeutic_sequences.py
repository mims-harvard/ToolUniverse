"""
TheraSAbDab_get_therapeutic_sequences

Get the full curated record for a clinical/approved therapeutic antibody from Thera-SAbDab by WHO...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def TheraSAbDab_get_therapeutic_sequences(
    name: Optional[str] = None,
    inn: Optional[str] = None,
    query: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the full curated record for a clinical/approved therapeutic antibody from Thera-SAbDab by WHO...

    Parameters
    ----------
    name : str
        WHO INN of the therapeutic antibody (e.g., 'adalimumab', 'abciximab', 'pembro...
    inn : str
        Alias for name.
    query : str
        Alias for name.
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
    _args = {
        k: v
        for k, v in {"name": name, "inn": inn, "query": query}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "TheraSAbDab_get_therapeutic_sequences",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["TheraSAbDab_get_therapeutic_sequences"]
