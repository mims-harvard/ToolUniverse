"""
nhanes_get_dataset_info

Get information about NHANES (National Health and Nutrition Examination Survey) datasets. NHANES ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def nhanes_get_dataset_info(
    year: Optional[str] = None,
    component: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get information about NHANES (National Health and Nutrition Examination Survey) datasets. NHANES ...

    Parameters
    ----------
    year : str
        NHANES cycle. Omit for the two most recent. There is no standalone 2019-2020 ...
    component : str
        Optional component type to filter datasets
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
        k: v for k, v in {"year": year, "component": component}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "nhanes_get_dataset_info",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["nhanes_get_dataset_info"]
