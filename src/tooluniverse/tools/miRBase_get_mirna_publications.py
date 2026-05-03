"""
miRBase_get_mirna_publications

Retrieve publications associated with a microRNA from RNAcentral. Returns publication titles, aut...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def miRBase_get_mirna_publications(
    rnacentral_id: str,
    page_size: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve publications associated with a microRNA from RNAcentral. Returns publication titles, aut...

    Parameters
    ----------
    rnacentral_id : str
        RNAcentral URS identifier (e.g., 'URS000039ED8D' for hsa-miR-21-5p). Use base...
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
            "name": "miRBase_get_mirna_publications",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["miRBase_get_mirna_publications"]
