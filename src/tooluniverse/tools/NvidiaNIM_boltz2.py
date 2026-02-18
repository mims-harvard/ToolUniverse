"""
NvidiaNIM_boltz2

Predict multi-molecular complex structure (proteins, DNA, RNA, ligands) using Boltz2 via NVIDIA N...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NvidiaNIM_boltz2(
    polymers: list[Any],
    ligands: Optional[list[Any]] = None,
    recycling_steps: Optional[int] = 3,
    sampling_steps: Optional[int] = 50,
    diffusion_samples: Optional[int] = 1,
    output_format: Optional[str] = "mmcif",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Predict multi-molecular complex structure (proteins, DNA, RNA, ligands) using Boltz2 via NVIDIA N...

    Parameters
    ----------
    polymers : list[Any]
        List of polymer molecules (1-12)
    ligands : list[Any]
        Ligands specified by CCD code OR SMILES (max 20)
    recycling_steps : int
        Number of recycling steps (1-6)
    sampling_steps : int
        Number of sampling steps (10-1000)
    diffusion_samples : int
        Number of structure samples (1-5)
    output_format : str

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
            "name": "NvidiaNIM_boltz2",
            "arguments": {
                "polymers": polymers,
                "ligands": ligands,
                "recycling_steps": recycling_steps,
                "sampling_steps": sampling_steps,
                "diffusion_samples": diffusion_samples,
                "output_format": output_format,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NvidiaNIM_boltz2"]
