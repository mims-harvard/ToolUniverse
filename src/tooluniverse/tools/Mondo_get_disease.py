"""
Mondo_get_disease

Get detailed information about a disease from the Mondo Disease Ontology by its MONDO ID. Returns...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Mondo_get_disease(
    disease_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed information about a disease from the Mondo Disease Ontology by its MONDO ID. Returns...

    Parameters
    ----------
    disease_id : str
        Mondo disease identifier. Examples: 'MONDO:0004975' (Alzheimer disease), 'MON...
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
    _args = {k: v for k, v in {"disease_id": disease_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "Mondo_get_disease",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Mondo_get_disease"]
