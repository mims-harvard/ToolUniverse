"""
ena_get_entry_history

Get version history for an ENA entry by accession number. Supports EMBL/GenBank accessions only (...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ena_get_entry_history(
    accession: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get version history for an ENA entry by accession number. Supports EMBL/GenBank accessions only (...

    Parameters
    ----------
    accession : str
        EMBL/GenBank accession number. NOT RefSeq (NC_*, NM_*, NP_*). Examples: 'U000...
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
    _args = {k: v for k, v in {"accession": accession}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "ena_get_entry_history",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ena_get_entry_history"]
