"""
PanelApp_search_panels

Search Genomics England PanelApp for gene panels used in clinical genetic testing. PanelApp is th...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PanelApp_search_panels(
    search: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search Genomics England PanelApp for gene panels used in clinical genetic testing. PanelApp is th...

    Parameters
    ----------
    search : str
        Search query for panel name or disease (e.g., 'breast cancer', 'epilepsy', 'h...
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
    _args = {k: v for k, v in {"search": search}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "PanelApp_search_panels",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PanelApp_search_panels"]
