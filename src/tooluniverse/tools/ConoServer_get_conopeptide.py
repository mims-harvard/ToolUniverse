"""
ConoServer_get_conopeptide

Get a full ConoServer conopeptide (cone-snail venom peptide) record by its ConoServer protein ID ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ConoServer_get_conopeptide(
    conoserver_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get a full ConoServer conopeptide (cone-snail venom peptide) record by its ConoServer protein ID ...

    Parameters
    ----------
    conoserver_id : str
        ConoServer protein ID, e.g. 'P00001' (alpha-conotoxin SI, sequence ICCNPACGPK...
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
    _args = {k: v for k, v in {"conoserver_id": conoserver_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "ConoServer_get_conopeptide",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ConoServer_get_conopeptide"]
