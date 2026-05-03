"""
MetabolomicsWorkbench_search_by_mz

Search metabolites by m/z (mass-to-charge ratio) value from mass spectrometry data. Essential for...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MetabolomicsWorkbench_search_by_mz(
    mz_value: float,
    adduct: Optional[str] = "M+H",
    tolerance: Optional[float] = 0.1,
    database: Optional[str] = "MB",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search metabolites by m/z (mass-to-charge ratio) value from mass spectrometry data. Essential for...

    Parameters
    ----------
    mz_value : float
        The m/z value to search for (e.g., 180.0634 for glucose [M+H]+).
    adduct : str
        Adduct type. Common values: 'M+H' (protonated), 'M-H' (deprotonated), 'M+Na' ...
    tolerance : float
        Mass tolerance in Daltons for the search.
    database : str
        Database to search: 'MB' (Metabolomics Workbench, default), 'LIPIDS', or 'REF...
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
            "mz_value": mz_value,
            "adduct": adduct,
            "tolerance": tolerance,
            "database": database,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MetabolomicsWorkbench_search_by_mz",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MetabolomicsWorkbench_search_by_mz"]
