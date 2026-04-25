"""
IDT_analyze_oligo

Analyze an oligonucleotide using the IDT OligoAnalyzer API. Calculates melting temperature (Tm), ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def IDT_analyze_oligo(
    sequence: str,
    na_concentration_mm: Optional[float | Any] = None,
    mg_concentration_mm: Optional[float | Any] = None,
    dntps_concentration_mm: Optional[float | Any] = None,
    oligo_concentration_um: Optional[float | Any] = None,
    oligo_type: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Analyze an oligonucleotide using the IDT OligoAnalyzer API. Calculates melting temperature (Tm), ...

    Parameters
    ----------
    sequence : str
        Oligonucleotide sequence (5' to 3'). Must contain only A, T, C, G (DNA) or A,...
    na_concentration_mm : float | Any
        Sodium (Na+) concentration in millimolar (mM). Affects Tm calculation. Typica...
    mg_concentration_mm : float | Any
        Magnesium (Mg2+) concentration in millimolar (mM). Stabilizes duplexes, raisi...
    dntps_concentration_mm : float | Any
        dNTPs concentration in millimolar (mM). dNTPs chelate Mg2+, reducing effectiv...
    oligo_concentration_um : float | Any
        Oligo concentration in micromolar (uM). Affects Tm slightly. Default: 0.25 uM.
    oligo_type : str | Any
        Type of oligonucleotide: 'DNA' or 'RNA'. Default: 'DNA'.
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
    _args = {k: v for k, v in {
        "sequence": sequence,
                "na_concentration_mm": na_concentration_mm,
                "mg_concentration_mm": mg_concentration_mm,
                "dntps_concentration_mm": dntps_concentration_mm,
                "oligo_concentration_um": oligo_concentration_um,
                "oligo_type": oligo_type
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "IDT_analyze_oligo",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["IDT_analyze_oligo"]
