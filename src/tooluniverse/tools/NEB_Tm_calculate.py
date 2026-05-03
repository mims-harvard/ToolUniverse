"""
NEB_Tm_calculate

Calculate primer melting temperature (Tm) and annealing temperature (Ta) using the NEB Tm Calcula...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NEB_Tm_calculate(
    primer_sequence: str,
    primer_sequence_2: Optional[str | Any] = None,
    polymerase: Optional[str | Any] = None,
    primer_concentration: Optional[int | Any] = None,
    monovalent_salt_mm: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Calculate primer melting temperature (Tm) and annealing temperature (Ta) using the NEB Tm Calcula...

    Parameters
    ----------
    primer_sequence : str
        Forward primer DNA sequence (5' to 3'). Must contain only A, T, C, G bases an...
    primer_sequence_2 : str | Any
        Optional reverse primer DNA sequence (5' to 3'). When provided, the API also ...
    polymerase : str | Any
        NEB polymerase product code. Determines buffer composition for Tm calculation...
    primer_concentration : int | Any
        Primer concentration in nanomolar (nM). Affects Tm calculation. Common values...
    monovalent_salt_mm : int | Any
        Monovalent salt concentration in mM. Only used when polymerase is 'custom'. T...
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
            "primer_sequence": primer_sequence,
            "primer_sequence_2": primer_sequence_2,
            "polymerase": polymerase,
            "primer_concentration": primer_concentration,
            "monovalent_salt_mm": monovalent_salt_mm,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "NEB_Tm_calculate",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NEB_Tm_calculate"]
