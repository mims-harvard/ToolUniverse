"""
ENCODE_search_biosamples

Search ENCODE biosamples (cell lines, tissues, primary cells) by organism, biosample type, or tre...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ENCODE_search_biosamples(
    organism: Optional[str] = None,
    biosample_type: Optional[str] = None,
    treatment: Optional[str] = None,
    limit: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search ENCODE biosamples (cell lines, tissues, primary cells) by organism, biosample type, or tre...

    Parameters
    ----------
    organism : str
        Organism filter (e.g., 'Homo sapiens', 'Mus musculus').
    biosample_type : str
        Biosample classification filter — maps to ENCODE's biosample_ontology.classif...
    treatment : str
        Treatment filter (e.g., 'interferon gamma', 'ethanol'). Use '*' to find any t...
    limit : int
        Maximum number of results to return (1–100).
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
            "organism": organism,
            "biosample_type": biosample_type,
            "treatment": treatment,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ENCODE_search_biosamples",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ENCODE_search_biosamples"]
