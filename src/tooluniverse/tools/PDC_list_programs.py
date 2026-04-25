"""
PDC_list_programs

List all programs and projects in the NCI Proteomics Data Commons (PDC). Returns the complete hie...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PDC_list_programs(
    operation: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    List all programs and projects in the NCI Proteomics Data Commons (PDC). Returns the complete hie...

    Parameters
    ----------
    operation : str
        Operation type
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {
        "operation": operation
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "PDC_list_programs",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["PDC_list_programs"]
