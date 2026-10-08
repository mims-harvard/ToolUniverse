"""
EBI_predict_membrane_topology

Predict transmembrane helices and signal peptides from a protein sequence using Phobius via EMBL-...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EBI_predict_membrane_topology(
    sequence: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Predict transmembrane helices and signal peptides from a protein sequence using Phobius via EMBL-...

    Parameters
    ----------
    sequence : str
        Protein sequence, FASTA or raw.
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
    _args = {k: v for k, v in {"sequence": sequence}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "EBI_predict_membrane_topology",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EBI_predict_membrane_topology"]
