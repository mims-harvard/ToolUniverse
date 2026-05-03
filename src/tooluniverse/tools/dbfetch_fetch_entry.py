"""
dbfetch_fetch_entry

Fetch a single database entry by ID from various databases (UniProt, PDB, etc.) in specified form...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def dbfetch_fetch_entry(
    db: str,
    id: str,
    format: Optional[str] = "fasta",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> str:
    """
    Fetch a single database entry by ID from various databases (UniProt, PDB, etc.) in specified form...

    Parameters
    ----------
    db : str
        Database name (e.g., 'uniprotkb', 'pdb', 'embl', 'ensembl')
    id : str
        Entry ID (e.g., UniProt accession 'P05067', PDB ID '1A2B')
    format : str
        Output format (e.g., 'fasta', 'xml', 'json', 'txt'). Default: 'fasta'
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    str
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v for k, v in {"db": db, "id": id, "format": format}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "dbfetch_fetch_entry",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["dbfetch_fetch_entry"]
