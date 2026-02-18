"""
NvidiaNIM_molmim

Controlled molecule generation using MolMIM via NVIDIA NIM. Generates molecules with optimized pr...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NvidiaNIM_molmim(
    smi: str,
    num_molecules: Optional[int] = 10,
    algorithm: Optional[str] = "CMA-ES",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Controlled molecule generation using MolMIM via NVIDIA NIM. Generates molecules with optimized pr...

    Parameters
    ----------
    smi : str
        Reference SMILES string for molecule generation
    num_molecules : int
        Number of molecules to generate (1-100)
    algorithm : str
        Optimization algorithm: CMA-ES (Covariance Matrix Adaptation Evolution Strate...
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
            "name": "NvidiaNIM_molmim",
            "arguments": {
                "smi": smi,
                "num_molecules": num_molecules,
                "algorithm": algorithm,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NvidiaNIM_molmim"]
