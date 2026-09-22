"""
PubMed_convert_article_ids

Convert between PubMed IDs (PMIDs), PubMed Central IDs (PMCIDs), DOIs and NIH manuscript IDs with...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PubMed_convert_article_ids(
    ids: list[str],
    id_type: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Convert between PubMed IDs (PMIDs), PubMed Central IDs (PMCIDs), DOIs and NIH manuscript IDs with...

    Parameters
    ----------
    ids : list[str]
        Identifiers to convert (PMIDs, PMCIDs, DOIs, NIHMS IDs), e.g. ['23193287', 'P...
    id_type : str
        Force the identifier type for every id instead of auto-detecting it.
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
    _args = {k: v for k, v in {"ids": ids, "id_type": id_type}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "PubMed_convert_article_ids",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PubMed_convert_article_ids"]
