"""
NvidiaNIM_proteinmpnn

Design protein sequences for a given backbone structure using ProteinMPNN via NVIDIA NIM (inverse...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NvidiaNIM_proteinmpnn(
    input_pdb: str,
    ca_only: Optional[bool] = False,
    use_soluble_model: Optional[bool] = False,
    sampling_temp: Optional[list[Any]] = None,
    num_seq_per_target: Optional[int] = 1,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Design protein sequences for a given backbone structure using ProteinMPNN via NVIDIA NIM (inverse...

    Parameters
    ----------
    input_pdb : str
        PDB format text of the backbone structure (ATOM records)
    ca_only : bool
        Use only CA atoms for design
    use_soluble_model : bool
        Use model trained on soluble proteins
    sampling_temp : list[Any]
        Sampling temperatures (0.1-0.3 recommended for high quality)
    num_seq_per_target : int
        Number of sequences to generate
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
    if sampling_temp is None:
        sampling_temp = [0.1]
    return get_shared_client().run_one_function(
        {
            "name": "NvidiaNIM_proteinmpnn",
            "arguments": {
                "input_pdb": input_pdb,
                "ca_only": ca_only,
                "use_soluble_model": use_soluble_model,
                "sampling_temp": sampling_temp,
                "num_seq_per_target": num_seq_per_target,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NvidiaNIM_proteinmpnn"]
