"""
UCSCCellBrowser_search_datasets

Search the UCSC Cell Browser catalog of 300+ curated single-cell datasets, filtering by organism,...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def UCSCCellBrowser_search_datasets(
    organism: Optional[str] = None,
    body_part: Optional[str] = None,
    disease: Optional[str] = None,
    keyword: Optional[str] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the UCSC Cell Browser catalog of 300+ curated single-cell datasets, filtering by organism,...

    Parameters
    ----------
    organism : str
        Substring match on organism, e.g. 'Human', 'Mouse', 'Zebrafish'.
    body_part : str
        Substring match on body part, e.g. 'brain', 'lung', 'retina', 'blood'.
    disease : str
        Substring match on disease, e.g. 'cancer', 'COVID-19', 'Healthy'.
    keyword : str
        Substring match on dataset name or display label, e.g. 'organoid'.
    limit : int
        Maximum datasets to return (default 25, max 100).
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
        for k, v in {
            "organism": organism,
            "body_part": body_part,
            "disease": disease,
            "keyword": keyword,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "UCSCCellBrowser_search_datasets",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["UCSCCellBrowser_search_datasets"]
