"""
ComplexPortal_get_complex

Get detailed information for a specific protein complex by Complex Portal ID (e.g., CPX-1234). Re...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ComplexPortal_get_complex(
    complex_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed information for a specific protein complex by Complex Portal ID (e.g., CPX-1234). Re...

    Parameters
    ----------
    complex_id : str
        Complex Portal accession ID (e.g., 'CPX-1', 'CPX-6512')
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
    _args = {k: v for k, v in {"complex_id": complex_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "ComplexPortal_get_complex",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ComplexPortal_get_complex"]
