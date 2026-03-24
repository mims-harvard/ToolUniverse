"""
MGnify_get_interpro

Get InterPro protein domain annotations from a MGnify metagenomics analysis. Returns InterPro ide...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MGnify_get_interpro(
    analysis_id: str,
    page_size: Optional[int] = 25,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get InterPro protein domain annotations from a MGnify metagenomics analysis. Returns InterPro ide...

    Parameters
    ----------
    analysis_id : str
        MGnify analysis accession (e.g., 'MGYA00585482'). Find IDs via MGnify_list_an...
    page_size : int
        Number of InterPro entries to return per page (default 25, max 100).
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {"analysis_id": analysis_id, "page_size": page_size}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MGnify_get_interpro",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MGnify_get_interpro"]
