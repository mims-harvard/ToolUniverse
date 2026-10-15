"""
IDT_check_self_dimer

Check an oligonucleotide for self-complementarity and homodimer (self-dimer) formation using the ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def IDT_check_self_dimer(
    sequence: str,
    na_concentration_mm: Optional[float] = None,
    mg_concentration_mm: Optional[float] = None,
    temperature_celsius: Optional[float] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Check an oligonucleotide for self-complementarity and homodimer (self-dimer) formation using the ...

    Parameters
    ----------
    sequence : str
        Oligonucleotide sequence (5' to 3'). Must contain only A, T, C, G, U bases. L...
    na_concentration_mm : float
        Sodium (Na+) concentration in millimolar (mM). Affects dimer stability. Defau...
    mg_concentration_mm : float
        Magnesium (Mg2+) concentration in millimolar (mM). Default: 0 mM.
    temperature_celsius : float
        Temperature in Celsius for dimer stability calculation. Use your expected ann...
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
            "sequence": sequence,
            "na_concentration_mm": na_concentration_mm,
            "mg_concentration_mm": mg_concentration_mm,
            "temperature_celsius": temperature_celsius,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "IDT_check_self_dimer",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["IDT_check_self_dimer"]
