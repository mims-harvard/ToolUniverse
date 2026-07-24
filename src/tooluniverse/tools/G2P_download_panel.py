"""
G2P_download_panel

Download the FULL content of a Gene2Phenotype (G2P) clinical panel as structured gene-disease rec...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def G2P_download_panel(
    panel: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Download the FULL content of a Gene2Phenotype (G2P) clinical panel as structured gene-disease rec...

    Parameters
    ----------
    panel : str
        Panel name (case-insensitive). Examples: 'Cancer', 'DD' (developmental disord...
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
    _args = {k: v for k, v in {"panel": panel}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "G2P_download_panel",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["G2P_download_panel"]
