"""
NvidiaNIM_diffdock

Blind molecular docking using DiffDock via NVIDIA NIM. Predict ligand binding poses without speci...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NvidiaNIM_diffdock(
    protein: str,
    ligand: str,
    ligand_file_type: Optional[str] = "sdf",
    num_poses: Optional[int] = 10,
    time_divisions: Optional[int] = 20,
    steps: Optional[int] = 18,
    save_trajectory: Optional[bool] = False,
    is_staged: Optional[bool] = False,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Blind molecular docking using DiffDock via NVIDIA NIM. Predict ligand binding poses without speci...

    Parameters
    ----------
    protein : str
        Protein structure: PDB content directly OR asset ID (if is_staged=true)
    ligand : str
        Ligand structure: SDF/MOL2 content directly OR asset ID (if is_staged=true)
    ligand_file_type : str
        Ligand file format
    num_poses : int
        Number of docking poses to generate (1-40)
    time_divisions : int
        Time divisions for diffusion
    steps : int
        Number of diffusion steps
    save_trajectory : bool
        Save diffusion trajectory
    is_staged : bool
        If true, protein and ligand are asset IDs (uploaded via NVCF assets API). If ...
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
            "name": "NvidiaNIM_diffdock",
            "arguments": {
                "protein": protein,
                "ligand": ligand,
                "ligand_file_type": ligand_file_type,
                "num_poses": num_poses,
                "time_divisions": time_divisions,
                "steps": steps,
                "save_trajectory": save_trajectory,
                "is_staged": is_staged,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NvidiaNIM_diffdock"]
