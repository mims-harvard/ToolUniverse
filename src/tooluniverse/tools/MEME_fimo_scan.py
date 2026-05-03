"""
MEME_fimo_scan

Scan DNA sequences for transcription factor (TF) binding motifs using FIMO (Find Individual Motif...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MEME_fimo_scan(
    operation: str,
    sequences: str,
    motif_text: str,
    pvalue_threshold: Optional[float | Any] = 0.0001,
    scan_rc: Optional[bool | Any] = True,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Scan DNA sequences for transcription factor (TF) binding motifs using FIMO (Find Individual Motif...

    Parameters
    ----------
    operation : str
        Operation type
    sequences : str
        DNA sequences in FASTA format to scan for motif occurrences. Example: '>seq1\...
    motif_text : str
        Motif(s) in MEME format. Must include the full MEME header (MEME version 5, A...
    pvalue_threshold : float | Any
        P-value threshold for reporting motif occurrences. Default 1e-4. Lower values...
    scan_rc : bool | Any
        If true (default), scan both strands. Set false to scan only the given strand.
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
    _args = {
        k: v
        for k, v in {
            "operation": operation,
            "sequences": sequences,
            "motif_text": motif_text,
            "pvalue_threshold": pvalue_threshold,
            "scan_rc": scan_rc,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MEME_fimo_scan",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MEME_fimo_scan"]
