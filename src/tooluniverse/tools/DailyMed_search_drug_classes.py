"""
DailyMed_search_drug_classes

Search the DailyMed database for FDA Established Pharmacologic Classes (EPC). Returns drug class ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DailyMed_search_drug_classes(
    drug_class_name: str,
    pagesize: Optional[int] = 100,
    page: Optional[int] = 1,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the DailyMed database for FDA Established Pharmacologic Classes (EPC). Returns drug class ...

    Parameters
    ----------
    drug_class_name : str
        Search term for drug class name (e.g., 'anti', 'kinase inhibitor', 'antibacte...
    pagesize : int
        Number of results per page (default: 100)
    page : int
        Page number for pagination (default: 1)
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

    return get_shared_client().run_one_function(
        {
            "name": "DailyMed_search_drug_classes",
            "arguments": {
                "drug_class_name": drug_class_name,
                "pagesize": pagesize,
                "page": page,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DailyMed_search_drug_classes"]
