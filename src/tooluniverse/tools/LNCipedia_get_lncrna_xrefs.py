"""
LNCipedia_get_lncrna_xrefs

Get cross-references for a long non-coding RNA from RNAcentral with explicit page pagination. Whi...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def LNCipedia_get_lncrna_xrefs(
    rnacentral_id: str,
    page_size: Optional[int] = 10,
    page: Optional[int] = 1,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get cross-references for a long non-coding RNA from RNAcentral with explicit page pagination. Whi...

    Parameters
    ----------
    rnacentral_id : str
        RNAcentral URS identifier (e.g., 'URS0002A146E4' for MALAT1). Use base URS ID...
    page_size : int
        Number of cross-references per page (1-50).
    page : int
        One-based RNAcentral page number. Continue with next_page.
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
        for k, v in {
            "rnacentral_id": rnacentral_id,
            "page_size": page_size,
            "page": page,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "LNCipedia_get_lncrna_xrefs",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["LNCipedia_get_lncrna_xrefs"]
