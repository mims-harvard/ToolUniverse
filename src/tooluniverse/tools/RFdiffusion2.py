from typing import Any, Optional, Callable
from ._shared_client import get_shared_client

def RFdiffusion2(
    contigs: str,
    input_pdb: Optional[str] = None,
    hotspot_res: Optional[list[str]] = None,
    num_designs: int = 1,
    diffusion_steps: int = 50,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    RFdiffusion2: Advanced protein structure and enzyme active site design.
    Provides finer control over enzyme scaffolding and active sites.
    
    Parameters
    ----------
    contigs : str
        Contig specification DSL.
    input_pdb : str, optional
        PDB structure for scaffolding/binder design.
    hotspot_res : list[str], optional
        Hotspot residues for design.
    num_designs : int, default 1
        Number of designs to generate.
    diffusion_steps : int, default 50
        Number of diffusion steps.
    """
    return get_shared_client().run_one_function(
        {
            "name": "RFdiffusion2",
            "arguments": {
                "contigs": contigs,
                "input_pdb": input_pdb,
                "hotspot_res": hotspot_res,
                "num_designs": num_designs,
                "diffusion_steps": diffusion_steps,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )

__all__ = ["RFdiffusion2"]
