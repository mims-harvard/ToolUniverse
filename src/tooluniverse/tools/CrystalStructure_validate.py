"""
CrystalStructure_validate

Validate crystal structure by computing theoretical density from unit cell parameters (a, b, c in...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CrystalStructure_validate(
    operation: str,
    a: float,
    Z: int,
    mw: float,
    b: Optional[float] = None,
    c: Optional[float] = None,
    alpha: Optional[float] = None,
    beta: Optional[float] = None,
    gamma: Optional[float] = None,
    reported_density: Optional[float] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Validate crystal structure by computing theoretical density from unit cell parameters (a, b, c in...

    Parameters
    ----------
    operation : str
        Operation type
    a : float
        Unit cell parameter a in Angstroms
    b : float
        Unit cell parameter b in Angstroms (defaults to a)
    c : float
        Unit cell parameter c in Angstroms (defaults to a)
    alpha : float
        Unit cell angle alpha in degrees (default 90)
    beta : float
        Unit cell angle beta in degrees (default 90)
    gamma : float
        Unit cell angle gamma in degrees (default 90)
    Z : int
        Number of formula units per unit cell
    mw : float
        Molecular weight in g/mol
    reported_density : float
        Optional reported density in g/cm^3 to compare against
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
            "a": a,
            "b": b,
            "c": c,
            "alpha": alpha,
            "beta": beta,
            "gamma": gamma,
            "Z": Z,
            "mw": mw,
            "reported_density": reported_density,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "CrystalStructure_validate",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CrystalStructure_validate"]
