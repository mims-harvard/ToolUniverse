"""
PROPKA_predict_pka

Predict protein pKa locally from one PDB model using optional PROPKA. Returns numbered groups, wa...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PROPKA_predict_pka(
    pdb_id: Optional[str] = None,
    pdb_path: Optional[str] = None,
    pdb_content: Optional[str] = None,
    ph_values: Optional[list[Any]] = None,
    timeout_seconds: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Predict protein pKa locally from one PDB model using optional PROPKA. Returns numbered groups, wa...

    Parameters
    ----------
    pdb_id : str
        Four-character RCSB PDB ID to download publicly. Provide exactly one source.
    pdb_path : str
        Local PDB file path; no upload. Provide exactly one source.
    pdb_content : str
        Inline PDB text; no upload. Provide exactly one source.
    ph_values : list[Any]
        pH values for independent-site fractions; defaults to [6.5, 7.4].
    timeout_seconds : int
        Bounded local worker runtime; defaults to 180 seconds.
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
            "pdb_id": pdb_id,
            "pdb_path": pdb_path,
            "pdb_content": pdb_content,
            "ph_values": ph_values,
            "timeout_seconds": timeout_seconds,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PROPKA_predict_pka",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PROPKA_predict_pka"]
