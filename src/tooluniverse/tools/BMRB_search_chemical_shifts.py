"""
BMRB_search_chemical_shifts

Query the distribution of assigned NMR chemical-shift values for a given residue/atom across ALL ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BMRB_search_chemical_shifts(
    comp_id: str,
    atom_id: str,
    shift_low: Optional[float] = None,
    shift_high: Optional[float] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Query the distribution of assigned NMR chemical-shift values for a given residue/atom across ALL ...

    Parameters
    ----------
    comp_id : str
        Residue/compound 3-letter code (e.g. 'HIS', 'ALA', 'GLY'). Nucleotides use 'A...
    atom_id : str
        Atom name within the residue (e.g. 'CA', 'CB', 'N', 'HA', 'H').
    shift_low : float
        Optional lower bound (ppm) on the chemical-shift value to filter results.
    shift_high : float
        Optional upper bound (ppm) on the chemical-shift value to filter results.
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
            "comp_id": comp_id,
            "atom_id": atom_id,
            "shift_low": shift_low,
            "shift_high": shift_high,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "BMRB_search_chemical_shifts",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BMRB_search_chemical_shifts"]
