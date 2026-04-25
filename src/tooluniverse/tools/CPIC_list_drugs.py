"""
CPIC_list_drugs

List all drugs in the CPIC database that have pharmacogenomic annotations. Returns drug names and...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CPIC_list_drugs(
    
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List all drugs in the CPIC database that have pharmacogenomic annotations. Returns drug names and...

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

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {
        
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "CPIC_list_drugs",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["CPIC_list_drugs"]
