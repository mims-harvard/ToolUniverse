"""
DDBJ_search_entries

Keyword search one DDBJ entry type (bioproject, biosample, sra-study, sra-experiment, sra-run, sr...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DDBJ_search_entries(
    entry_type: str,
    keywords: str,
    organism_taxid: Optional[str | int] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Keyword search one DDBJ entry type (bioproject, biosample, sra-study, sra-experiment, sra-run, sr...

    Parameters
    ----------
    entry_type : str
        Which DDBJ record type to search.
    keywords : str
        Free-text search terms, e.g. 'daptomycin resistance'.
    organism_taxid : str | int
        Optional NCBI taxonomy ID filter, e.g. 9606 (human).
    limit : int
        Max entries to return, 1-100. Default 25.
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
            "entry_type": entry_type,
            "keywords": keywords,
            "organism_taxid": organism_taxid,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "DDBJ_search_entries",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DDBJ_search_entries"]
