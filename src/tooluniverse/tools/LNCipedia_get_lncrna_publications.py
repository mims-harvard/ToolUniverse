"""
LNCipedia_get_lncrna_publications

Retrieve publications associated with a long non-coding RNA from RNAcentral. Returns publication ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def LNCipedia_get_lncrna_publications(
    rnacentral_id: str,
    page_size: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve publications associated with a long non-coding RNA from RNAcentral. Returns publication ...

    Parameters
    ----------
    rnacentral_id : str
        RNAcentral URS identifier (e.g., 'URS0002A146E4' for MALAT1). Use base URS ID...
    page_size : int
        Number of publications to return (1-50). Default: 10.
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
        for k, v in {"rnacentral_id": rnacentral_id, "page_size": page_size}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "LNCipedia_get_lncrna_publications",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["LNCipedia_get_lncrna_publications"]
