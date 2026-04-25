"""
Sequence_stats

Compute basic statistics for a DNA, RNA, or protein sequence. Auto-detects sequence type, reports...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Sequence_stats(
    operation: str,
    sequence: Optional[str] = None,
    uniprot_id: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Compute basic statistics for a DNA, RNA, or protein sequence. Auto-detects sequence type, reports...

    Parameters
    ----------
    operation : str
        Operation type
    sequence : str
        Sequence string. Optional if uniprot_id is provided.
    uniprot_id : str
        UniProt accession to fetch protein sequence from. Optional if sequence is pro...
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
            "operation": operation,
            "sequence": sequence,
            "uniprot_id": uniprot_id,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Sequence_stats",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Sequence_stats"]
