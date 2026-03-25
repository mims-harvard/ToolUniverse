"""
HuBMAP_list_organs

List all organs available in the HuBMAP (Human BioMolecular Atlas Program) atlas. Returns organ n...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def HuBMAP_list_organs(
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List all organs available in the HuBMAP (Human BioMolecular Atlas Program) atlas. Returns organ n...

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
    _args = {k: v for k, v in {}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "HuBMAP_list_organs",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["HuBMAP_list_organs"]
