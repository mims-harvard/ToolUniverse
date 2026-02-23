"""
GitHub_get_repository

Get detailed metadata for a specific GitHub public repository. Returns full repository informatio...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GitHub_get_repository(
    owner: str,
    repo: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed metadata for a specific GitHub public repository. Returns full repository informatio...

    Parameters
    ----------
    owner : str
        Repository owner (username or organization). Examples: 'deepmind', 'bioconduc...
    repo : str
        Repository name. Examples: 'alphafold', 'pytorch', 'pandas', 'scikit-learn', ...
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
        {"name": "GitHub_get_repository", "arguments": {"owner": owner, "repo": repo}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GitHub_get_repository"]
