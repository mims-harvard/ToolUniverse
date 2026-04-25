"""
ModelDB_list_models

List all computational neuroscience model IDs from ModelDB, optionally filtered by simulation env...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ModelDB_list_models(
    modeling_application: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List all computational neuroscience model IDs from ModelDB, optionally filtered by simulation env...

    Parameters
    ----------
    modeling_application : str
        Filter by simulation environment name. Case-sensitive. Common values: 'NEURON...
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
        "modeling_application": modeling_application
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "ModelDB_list_models",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["ModelDB_list_models"]
