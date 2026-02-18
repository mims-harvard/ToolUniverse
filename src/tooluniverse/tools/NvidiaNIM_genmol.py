"""
NvidiaNIM_genmol

Generate molecules using GenMol via NVIDIA NIM. Input: SMILES/SAFE template with masked regions. ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NvidiaNIM_genmol(
    smiles: str,
    num_molecules: Optional[int] = 5,
    temperature: Optional[float] = 2.0,
    noise: Optional[float] = 1.0,
    step_size: Optional[int] = 1,
    scoring: Optional[str] = "QED",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Generate molecules using GenMol via NVIDIA NIM. Input: SMILES/SAFE template with masked regions. ...

    Parameters
    ----------
    smiles : str
        SAFE/SMILES template with masked fragments. Use [*{min-max}] for variable-len...
    num_molecules : int
        Number of molecules to generate (1-1000)
    temperature : float
        Sampling temperature (0.01-10.0). Higher = more diverse
    noise : float
        Noise level for generation (0-2.0)
    step_size : int
        Step size for sampling
    scoring : str
        Property to score generated molecules
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

    return get_shared_client().run_one_function(
        {
            "name": "NvidiaNIM_genmol",
            "arguments": {
                "smiles": smiles,
                "num_molecules": num_molecules,
                "temperature": temperature,
                "noise": noise,
                "step_size": step_size,
                "scoring": scoring,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NvidiaNIM_genmol"]
