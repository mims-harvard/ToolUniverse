"""
WHO_Guideline_Full_Text

Fetch full text content from a WHO (World Health Organization) guideline publication page. Extrac...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def WHO_Guideline_Full_Text(
    url: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Fetch full text content from a WHO (World Health Organization) guideline publication page. Extrac...

    Parameters
    ----------
    url : str
        Full URL of the WHO publication page (e.g., 'https://www.who.int/publications...
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
        {"name": "WHO_Guideline_Full_Text", "arguments": {"url": url}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["WHO_Guideline_Full_Text"]
