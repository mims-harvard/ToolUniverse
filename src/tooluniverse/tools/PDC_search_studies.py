"""
PDC_search_studies

Search the NCI Proteomics Data Commons (PDC) for cancer proteomics studies by keyword. PDC houses...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PDC_search_studies(
    operation: str,
    query: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search the NCI Proteomics Data Commons (PDC) for cancer proteomics studies by keyword. PDC houses...

    Parameters
    ----------
    operation : str
        Operation type
    query : str
        Search keyword for studies. Can be disease name (Breast, Lung, Renal), progra...
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
        for k, v in {"operation": operation, "query": query}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PDC_search_studies",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PDC_search_studies"]
