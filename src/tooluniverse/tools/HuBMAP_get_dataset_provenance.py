"""
HuBMAP_get_dataset_provenance

Retrieve a HuBMAP dataset's biological provenance lineage: the ordered chain of ancestor entities...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def HuBMAP_get_dataset_provenance(
    uuid: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve a HuBMAP dataset's biological provenance lineage: the ordered chain of ancestor entities...

    Parameters
    ----------
    uuid : str
        HuBMAP dataset UUID (32-char hex, e.g. 'b1ca0a28b39e5ee6a252403e03247db6') or...
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
    _args = {k: v for k, v in {"uuid": uuid}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "HuBMAP_get_dataset_provenance",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["HuBMAP_get_dataset_provenance"]
