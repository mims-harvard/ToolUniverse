"""
ORCID_get_works

Get the publication list (works) for a researcher by ORCID iD. Returns all works associated with ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ORCID_get_works(
    orcid_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the publication list (works) for a researcher by ORCID iD. Returns all works associated with ...

    Parameters
    ----------
    orcid_id : str
        ORCID iD in format XXXX-XXXX-XXXX-XXXX (e.g., '0000-0001-9161-999X' for Jenni...
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
        {"name": "ORCID_get_works", "arguments": {"orcid_id": orcid_id}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ORCID_get_works"]
