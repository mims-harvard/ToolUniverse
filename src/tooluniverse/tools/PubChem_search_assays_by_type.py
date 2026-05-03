"""
PubChem_search_assays_by_type

Search bioassays by assay type. Types: screening (HTS), confirmatory, doseresponse, summary, cell...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PubChem_search_assays_by_type(
    assay_type: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search bioassays by assay type. Types: screening (HTS), confirmatory, doseresponse, summary, cell...

    Parameters
    ----------
    assay_type : str
        Type of assay to search for
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
    _args = {k: v for k, v in {"assay_type": assay_type}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "PubChem_search_assays_by_type",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PubChem_search_assays_by_type"]
