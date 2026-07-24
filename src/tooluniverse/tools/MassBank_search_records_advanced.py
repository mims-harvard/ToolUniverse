"""
MassBank_search_records_advanced

Filtered search of the MassBank Europe spectral library using one or more criteria combined as AN...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MassBank_search_records_advanced(
    exact_mass: Optional[float] = None,
    mass_tolerance: Optional[float] = None,
    peaks: Optional[str] = None,
    neutral_loss: Optional[str] = None,
    ion_mode: Optional[str] = None,
    ms_type: Optional[str] = None,
    instrument_type: Optional[str] = None,
    substructure: Optional[str] = None,
    contributor: Optional[str] = None,
    compound_class: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Filtered search of the MassBank Europe spectral library using one or more criteria combined as AN...

    Parameters
    ----------
    exact_mass : float
        Exact monoisotopic mass to match (Da). Combine with mass_tolerance. Example: ...
    mass_tolerance : float
        Mass tolerance window in Da for exact_mass (e.g., 0.005). Only meaningful tog...
    peaks : str
        Fragment peak m/z value(s) that must be present (e.g., '138.0661').
    neutral_loss : str
        Neutral loss m/z difference that must be present (e.g., '18.0106' for water l...
    ion_mode : str
        Ionization polarity: 'POSITIVE' or 'NEGATIVE'.
    ms_type : str
        MS level: 'MS', 'MS2', or 'MS3'.
    instrument_type : str
        Instrument type filter (e.g., 'LC-ESI-QTOF', 'LC-ESI-ITFT').
    substructure : str
        SMILES/SMARTS substructure that the compound must contain (e.g., 'c1ccccc1' f...
    contributor : str
        Contributing institution/library filter.
    compound_class : str
        Chemical compound class filter.
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
            "exact_mass": exact_mass,
            "mass_tolerance": mass_tolerance,
            "peaks": peaks,
            "neutral_loss": neutral_loss,
            "ion_mode": ion_mode,
            "ms_type": ms_type,
            "instrument_type": instrument_type,
            "substructure": substructure,
            "contributor": contributor,
            "compound_class": compound_class,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MassBank_search_records_advanced",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MassBank_search_records_advanced"]
