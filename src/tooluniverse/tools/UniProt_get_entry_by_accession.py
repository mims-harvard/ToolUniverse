"""
UniProt_get_entry_by_accession

Get a UniProtKB entry by accession. Returns a compact summary by default (protein name, gene, org...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def UniProt_get_entry_by_accession(
    accession: str,
    compact: Optional[bool] = True,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get a UniProtKB entry by accession. Returns a compact summary by default (protein name, gene, org...

    Parameters
    ----------
    accession : str
        UniProtKB entry accession, e.g., P05067.
    compact : bool
        Return compact summary (default true). Set false for full raw JSON entry.
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
    _args = {k: v for k, v in {
        "accession": accession,
                "compact": compact
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "UniProt_get_entry_by_accession",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["UniProt_get_entry_by_accession"]
