"""
Hemolytik2_search_peptides

Search Hemolytik 2.0 (Raghava lab, IIITD) for experimentally validated HEMOLYTIC / TOXIC peptide ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Hemolytik2_search_peptides(
    dataValue: str,
    dataType: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search Hemolytik 2.0 (Raghava lab, IIITD) for experimentally validated HEMOLYTIC / TOXIC peptide ...

    Parameters
    ----------
    dataType : str
        Field to filter on. One of: 'nature' (peptide nature, e.g. Anticancer, Antimi...
    dataValue : str
        Value to match for the chosen dataType. Examples: 'Anticancer' (with dataType...
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
    _args = {
        k: v
        for k, v in {"dataType": dataType, "dataValue": dataValue}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Hemolytik2_search_peptides",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Hemolytik2_search_peptides"]
