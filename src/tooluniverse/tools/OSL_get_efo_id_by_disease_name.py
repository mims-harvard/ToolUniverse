"""
OSL_get_efo_id_by_disease_name

Legacy helper to find an EFO term ID from a disease name using EMBL-EBI OLS search.

Returns the ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OSL_get_efo_id_by_disease_name(
    disease: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
        Legacy helper to find an EFO term ID from a disease name using EMBL-EBI OLS search.

    Returns the ...

        Parameters
        ----------
        disease : str
            Disease name or free-text query (e.g., 'diabetes mellitus').
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
    _args = {k: v for k, v in {"disease": disease}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "OSL_get_efo_id_by_disease_name",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OSL_get_efo_id_by_disease_name"]
