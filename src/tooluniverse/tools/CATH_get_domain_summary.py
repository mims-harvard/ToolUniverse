"""
CATH_get_domain_summary

Get CATH structural classification for a specific protein domain from PDB. Domains are identified...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CATH_get_domain_summary(
    domain_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get CATH structural classification for a specific protein domain from PDB. Domains are identified...

    Parameters
    ----------
    domain_id : str
        CATH domain ID: PDB code (4 chars) + chain (1 char) + domain number (2 digits...
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
    _args = {k: v for k, v in {"domain_id": domain_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "CATH_get_domain_summary",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CATH_get_domain_summary"]
