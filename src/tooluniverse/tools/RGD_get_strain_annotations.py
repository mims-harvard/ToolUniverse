"""
RGD_get_strain_annotations

Get curated disease, phenotype, and variant-trait ontology annotations for a rat strain from the ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def RGD_get_strain_annotations(
    symbol: str,
    category: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get curated disease, phenotype, and variant-trait ontology annotations for a rat strain from the ...

    Parameters
    ----------
    symbol : str
        Exact rat strain symbol (case-insensitive), e.g. 'SHR', 'BN', 'SS'.
    category : str
        Optional annotation category filter: 'disease', 'phenotype', 'strain', 'pathw...
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
    _args = {
        k: v
        for k, v in {"symbol": symbol, "category": category}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "RGD_get_strain_annotations",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["RGD_get_strain_annotations"]
