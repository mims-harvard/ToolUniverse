"""
NvidiaNIM_rfdiffusion

De novo protein design using RFdiffusion via NVIDIA NIM. Generate novel protein structures, binde...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NvidiaNIM_rfdiffusion(
    contigs: str,
    input_pdb: str,
    hotspot_res: Optional[list[str]] = None,
    diffusion_steps: Optional[int] = 15,
    random_seed: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    De novo protein design using RFdiffusion via NVIDIA NIM. Generate novel protein structures, binde...

    Parameters
    ----------
    contigs : str
        Contig specification DSL. Format: 'ChainStart-End/gap length'. Example: 'A20-...
    input_pdb : str
        PDB structure for scaffolding/binder design (ATOM records only). Required by ...
    hotspot_res : list[str]
        Hotspot residues for binder design (e.g., ['A50', 'A51', 'A52'])
    diffusion_steps : int
        Number of diffusion steps (15-50)
    random_seed : int
        Random seed for reproducibility
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
            "name": "NvidiaNIM_rfdiffusion",
            "arguments": {
                "contigs": contigs,
                "input_pdb": input_pdb,
                "hotspot_res": hotspot_res,
                "diffusion_steps": diffusion_steps,
                "random_seed": random_seed,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NvidiaNIM_rfdiffusion"]
