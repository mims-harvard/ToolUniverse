"""
AMPSphere_get_family

Retrieve full detail for an AMPSphere protein family (SPHERE cluster) by accession (e.g. 'SPHERE-...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def AMPSphere_get_family(
    accession: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve full detail for an AMPSphere protein family (SPHERE cluster) by accession (e.g. 'SPHERE-...

    Parameters
    ----------
    accession : str
        SPHERE family accession. Example: 'SPHERE-III.001_396' (23 member AMPs, conse...
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
    _args = {k: v for k, v in {"accession": accession}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "AMPSphere_get_family",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["AMPSphere_get_family"]
