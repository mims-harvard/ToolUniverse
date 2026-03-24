"""
GenCC_search_disease

Find genes with validity evidence for a disease from GenCC (Gene Curation Coalition). Search by d...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GenCC_search_disease(
    operation: Optional[str] = None,
    disease: Optional[str] = None,
    disease_name: Optional[str] = None,
    classification: Optional[str] = "",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Find genes with validity evidence for a disease from GenCC (Gene Curation Coalition). Search by d...

    Parameters
    ----------
    operation : str
        Operation type (fixed: search_disease)
    disease : str
        Disease name or ID to search (e.g., 'Marfan syndrome', 'MONDO:0007947', 'brea...
    disease_name : str
        Alias for disease. Disease name or ID to search.
    classification : str
        Optional filter by classification level (e.g., Definitive, Strong)
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
        for k, v in {
            "operation": operation,
            "disease": disease,
            "disease_name": disease_name,
            "classification": classification,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GenCC_search_disease",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GenCC_search_disease"]
