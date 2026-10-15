"""
EBI_scan_pfam_domains

Scan a protein sequence against Pfam HMMs via EMBL-EBI PfamScan and return each matched domain wi...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EBI_scan_pfam_domains(
    sequence: str,
    database: Optional[str] = None,
    evalue: Optional[float] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Scan a protein sequence against Pfam HMMs via EMBL-EBI PfamScan and return each matched domain wi...

    Parameters
    ----------
    sequence : str
        Protein sequence, FASTA or raw.
    database : str
        'pfam-a' (default).
    evalue : float
        E-value cutoff, e.g. 0.001.
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
            "sequence": sequence,
            "database": database,
            "evalue": evalue,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EBI_scan_pfam_domains",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EBI_scan_pfam_domains"]
