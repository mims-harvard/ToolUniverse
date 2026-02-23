"""
NICE_Guideline_Full_Text

Fetch complete full text content from a NICE clinical guideline page. Takes a NICE guideline URL ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NICE_Guideline_Full_Text(
    url: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Fetch complete full text content from a NICE clinical guideline page. Takes a NICE guideline URL ...

    Parameters
    ----------
    url : str
        Full URL of the NICE guideline page (e.g., 'https://www.nice.org.uk/guidance/...
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
        {"name": "NICE_Guideline_Full_Text", "arguments": {"url": url}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NICE_Guideline_Full_Text"]
