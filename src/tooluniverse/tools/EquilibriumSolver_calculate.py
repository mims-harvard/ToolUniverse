"""
EquilibriumSolver_calculate

Solve chemical equilibrium problems: simple Ksp dissolution, Ksp with complex formation (amphoter...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EquilibriumSolver_calculate(
    operation: str,
    Ksp: float,
    Kf: Optional[float | Any] = None,
    stoich_cation: Optional[int | Any] = 1,
    stoich_anion: Optional[int | Any] = 1,
    common_ion_conc: Optional[float | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Solve chemical equilibrium problems: simple Ksp dissolution, Ksp with complex formation (amphoter...

    Parameters
    ----------
    operation : str
        Problem type: 'ksp_simple' for basic dissolution, 'ksp_complex' for dissoluti...
    Ksp : float
        Solubility product constant (Ksp).
    Kf : float | Any
        Formation constant for complex ion (required for ksp_complex mode).
    stoich_cation : int | Any
        Stoichiometric coefficient 'a' for the cation in MaXb (default: 1).
    stoich_anion : int | Any
        Stoichiometric coefficient 'b' for the anion in MaXb (default: 1).
    common_ion_conc : float | Any
        Common ion concentration in mol/L (required for common_ion mode).
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
            "Ksp": Ksp,
            "Kf": Kf,
            "stoich_cation": stoich_cation,
            "stoich_anion": stoich_anion,
            "common_ion_conc": common_ion_conc,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EquilibriumSolver_calculate",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EquilibriumSolver_calculate"]
