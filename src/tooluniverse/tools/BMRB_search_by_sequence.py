"""
BMRB_search_by_sequence

Search ALL BMRB entries by protein or nucleic-acid sequence similarity (FASTA/BLAST). Given a sin...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BMRB_search_by_sequence(
    sequence: str,
    type_: Optional[str] = "polymer",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search ALL BMRB entries by protein or nucleic-acid sequence similarity (FASTA/BLAST). Given a sin...

    Parameters
    ----------
    sequence : str
        Single-letter amino-acid or nucleotide sequence to search (no FASTA header li...
    type_ : str
        Sequence database to search: 'polymer' (default; proteins and nucleic acids) ...
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
        k: v for k, v in {"sequence": sequence, "type": type_}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "BMRB_search_by_sequence",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BMRB_search_by_sequence"]
