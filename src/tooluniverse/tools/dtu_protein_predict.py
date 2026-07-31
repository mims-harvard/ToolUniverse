"""
dtu_protein_predict

Run DTU Health Tech machine-learning protein predictors on a protein sequence via the BioLib clou...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def dtu_protein_predict(
    model: Optional[str] = "deeptmhmm",
    sequence: Optional[str] = None,
    fasta: Optional[str] = None,
    fasta_path: Optional[str] = None,
    max_wait_time: Optional[int] = 600,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Run DTU Health Tech machine-learning protein predictors on a protein sequence via the BioLib clou...

    Parameters
    ----------
    model : str
        Which predictor to run: 'deeptmhmm' (transmembrane topology), 'signalp' (sign...
    sequence : str
        Protein input as inline FASTA text (one or more '>header' records) or a bare ...
    fasta : str
        Alias for 'sequence'. Inline FASTA text or a bare amino-acid string.
    fasta_path : str
        Path to a local FASTA (.fasta/.fa) file containing one or more protein record...
    max_wait_time : int
        Maximum seconds to wait for the BioLib cloud job to finish (default 600, min ...
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
            "model": model,
            "sequence": sequence,
            "fasta": fasta,
            "fasta_path": fasta_path,
            "max_wait_time": max_wait_time,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "dtu_protein_predict",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["dtu_protein_predict"]
