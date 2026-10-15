"""
DANDI_get_dataset

Retrieve full metadata for one DANDI dandiset: description, species, data standard, license, and ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DANDI_get_dataset(
    dandiset_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve full metadata for one DANDI dandiset: description, species, data standard, license, and ...

    Parameters
    ----------
    dandiset_id : str
        DANDI dataset identifier, e.g. '000020'.
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
    _args = {k: v for k, v in {"dandiset_id": dandiset_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "DANDI_get_dataset",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DANDI_get_dataset"]
