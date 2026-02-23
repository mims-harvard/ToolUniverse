"""
PanelApp_get_panel

Get the full gene list and details for a specific Genomics England PanelApp gene panel by panel I...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PanelApp_get_panel(
    panel_id: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the full gene list and details for a specific Genomics England PanelApp gene panel by panel I...

    Parameters
    ----------
    panel_id : int
        PanelApp panel ID (e.g., 504 for 'Inherited polyposis and early onset colorec...
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
        {"name": "PanelApp_get_panel", "arguments": {"panel_id": panel_id}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PanelApp_get_panel"]
