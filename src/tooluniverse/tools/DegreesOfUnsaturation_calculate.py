"""
DegreesOfUnsaturation_calculate

Calculate degrees of unsaturation (DoU, also called index of hydrogen deficiency or degree of uns...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DegreesOfUnsaturation_calculate(
    operation: str,
    formula: Optional[str] = None,
    C: Optional[int] = None,
    H: Optional[int] = None,
    N: Optional[int] = None,
    oxygen: Optional[int] = None,
    S: Optional[int] = None,
    F: Optional[int] = None,
    Cl: Optional[int] = None,
    Br: Optional[int] = None,
    iodine: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Calculate degrees of unsaturation (DoU, also called index of hydrogen deficiency or degree of uns...

    Parameters
    ----------
    operation : str
        Operation type
    formula : str
        Molecular formula string (e.g., 'C6H6', 'C8H15ClN2O2'). Alternative to explic...
    C : int
        Number of carbon atoms (use if formula not provided)
    H : int
        Number of hydrogen atoms (use if formula not provided)
    N : int
        Number of nitrogen atoms (default 0)
    oxygen : int
        Number of oxygen atoms (does not affect DoU, tracked for formula display)
    S : int
        Number of sulfur atoms (does not affect DoU)
    F : int
        Number of fluorine atoms
    Cl : int
        Number of chlorine atoms
    Br : int
        Number of bromine atoms
    iodine : int
        Number of iodine atoms
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
            "operation": operation,
            "formula": formula,
            "C": C,
            "H": H,
            "N": N,
            "O": oxygen,
            "S": S,
            "F": F,
            "Cl": Cl,
            "Br": Br,
            "I": iodine,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "DegreesOfUnsaturation_calculate",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DegreesOfUnsaturation_calculate"]
