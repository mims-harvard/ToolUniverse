"""
DNA_golden_gate_design

Design Golden Gate Assembly parts with Type IIS restriction enzyme sites (BsaI or BbsI). Assigns ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DNA_golden_gate_design(
    operation: str,
    parts: list[str],
    enzyme: Optional[str | Any] = "BsaI",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Design Golden Gate Assembly parts with Type IIS restriction enzyme sites (BsaI or BbsI). Assigns ...

    Parameters
    ----------
    operation : str
        Operation type
    parts : list[str]
        List of DNA part sequences to assemble (at least 2). A, T, G, C only.
    enzyme : str | Any
        Type IIS restriction enzyme to use. Options: 'BsaI' (default) or 'BbsI'.
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
        {
            "name": "DNA_golden_gate_design",
            "arguments": {"operation": operation, "parts": parts, "enzyme": enzyme},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DNA_golden_gate_design"]
