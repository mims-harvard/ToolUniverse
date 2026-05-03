"""
GitHub_get_user_profile

Get a public GitHub user profile by username. Returns user metadata including name, bio, company,...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GitHub_get_user_profile(
    username: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get a public GitHub user profile by username. Returns user metadata including name, bio, company,...

    Parameters
    ----------
    username : str
        GitHub username. Examples: 'torvalds' (Linus Torvalds), 'gvanrossum' (Guido v...
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
    _args = {k: v for k, v in {"username": username}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "GitHub_get_user_profile",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GitHub_get_user_profile"]
