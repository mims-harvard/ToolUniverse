"""
IDR_list_values_for_key

List every distinct value (and the number of images annotated with it) for one IDR metadata key, ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def IDR_list_values_for_key(
    key: str,
    resource: Optional[str] = None,
    max_results: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List every distinct value (and the number of images annotated with it) for one IDR metadata key, ...

    Parameters
    ----------
    key : str
        The metadata attribute whose values to enumerate, e.g. 'Organism', 'Phenotype...
    resource : str
        Resource type. Default 'image'.
    max_results : int
        Optional client-side cap on the number of values returned.
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
    _args = {
        k: v
        for k, v in {
            "key": key,
            "resource": resource,
            "max_results": max_results,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "IDR_list_values_for_key",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["IDR_list_values_for_key"]
