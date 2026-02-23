"""
CPIC_list_guidelines

List all CPIC pharmacogenomic guidelines. Returns 31 evidence-based guidelines for using pharmaco...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CPIC_list_guidelines(
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List all CPIC pharmacogenomic guidelines. Returns 31 evidence-based guidelines for using pharmaco...

    Parameters
    ----------
    No parameters
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
        {"name": "CPIC_list_guidelines", "arguments": {}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CPIC_list_guidelines"]
