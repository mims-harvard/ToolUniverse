"""
geant4_depth_dose_simulation

Monte Carlo depth-dose simulation with GEANT4: fire a particle beam into a slab of one NIST mater...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def geant4_depth_dose_simulation(
    particle: Optional[str] = None,
    energy_mev: Optional[float] = None,
    material: Optional[str] = None,
    thickness_cm: Optional[float] = None,
    bins: Optional[int] = None,
    events: Optional[int] = None,
    timeout_seconds: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Monte Carlo depth-dose simulation with GEANT4: fire a particle beam into a slab of one NIST mater...

    Parameters
    ----------
    particle : str
        Beam particle (default 'proton').
    energy_mev : float
        Kinetic energy of each primary particle in MeV, from 0.001 to 100000 (default...
    material : str
        Target material, a NIST name GEANT4 builds itself (default 'G4_WATER').
    thickness_cm : float
        Depth of the target along the beam in cm, from 0.01 to 500 (default 20). Make...
    bins : int
        Number of equal depth bins to score, from 1 to 2000 (default 100). thickness_...
    events : int
        Primary particles to simulate, from 1 to 200000 (default 200). More events me...
    timeout_seconds : int
        Give up after this many seconds, from 1 to 1800 (default 600).
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
            "particle": particle,
            "energy_mev": energy_mev,
            "material": material,
            "thickness_cm": thickness_cm,
            "bins": bins,
            "events": events,
            "timeout_seconds": timeout_seconds,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "geant4_depth_dose_simulation",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["geant4_depth_dose_simulation"]
