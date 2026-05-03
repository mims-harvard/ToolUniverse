"""
FDA_get_drug_generic_name

Get the drug’s generic name based on the drug's generic or brand name.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FDA_get_drug_generic_name(
    drug_name: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get the drug’s generic name based on the drug's generic or brand name.

    Parameters
    ----------
    drug_name : str
        The generic or brand name of the drug.
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
    _args = {k: v for k, v in {"drug_name": drug_name}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "FDA_get_drug_generic_name",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FDA_get_drug_generic_name"]
