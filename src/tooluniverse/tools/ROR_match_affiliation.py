"""
ROR_match_affiliation

Resolve a free-text author affiliation string (as printed in a paper, e.g. 'Department of Chemist...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ROR_match_affiliation(
    affiliation: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Resolve a free-text author affiliation string (as printed in a paper, e.g. 'Department of Chemist...

    Parameters
    ----------
    affiliation : str
        Raw affiliation string to match, typically copied from a publication byline (...
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
    _args = {k: v for k, v in {"affiliation": affiliation}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "ROR_match_affiliation",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ROR_match_affiliation"]
