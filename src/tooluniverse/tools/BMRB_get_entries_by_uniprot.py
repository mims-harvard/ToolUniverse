"""
BMRB_get_entries_by_uniprot

Find BMRB NMR entries for a protein using its UniProt accession. Returns NMR data entries associa...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BMRB_get_entries_by_uniprot(
    uniprot_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Find BMRB NMR entries for a protein using its UniProt accession. Returns NMR data entries associa...

    Parameters
    ----------
    uniprot_id : str
        UniProt accession (e.g., 'P62988' for ubiquitin, 'P0DTD1' for SARS-CoV-2 poly...
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
            "name": "BMRB_get_entries_by_uniprot",
            "arguments": {"uniprot_id": uniprot_id},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BMRB_get_entries_by_uniprot"]
