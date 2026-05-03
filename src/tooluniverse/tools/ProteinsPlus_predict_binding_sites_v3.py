"""
ProteinsPlus_predict_binding_sites_v3

Predict druggable binding sites using DoGSite3 algorithm with ligand-biased grid option. Enhanced...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ProteinsPlus_predict_binding_sites_v3(
    pdb_id: str,
    chain: Optional[str] = None,
    ligand: Optional[str] = None,
    ligand_bias: Optional[bool] = None,
    analysis_detail: Optional[str] = None,
    druggability: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Predict druggable binding sites using DoGSite3 algorithm with ligand-biased grid option. Enhanced...

    Parameters
    ----------
    pdb_id : str
        PDB identifier (e.g., '1KZK', '2OZR', '4HHB'). Required.
    chain : str
        Specific chain to analyze (e.g., 'A'). Optional - if not provided, all chains...
    ligand : str
        Reference ligand identifier in format 'residue_name_residue_chain_residue_num...
    ligand_bias : bool
        Enable ligand-biased grid calculations (true) or standard detection (false). ...
    analysis_detail : str
        Analysis level: '0' for pockets only (faster), '1' for pockets and subpockets...
    druggability : str
        Prediction granularity: '0' for geometric properties only, '1' for properties...
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
            "pdb_id": pdb_id,
            "chain": chain,
            "ligand": ligand,
            "ligand_bias": ligand_bias,
            "analysis_detail": analysis_detail,
            "druggability": druggability,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ProteinsPlus_predict_binding_sites_v3",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ProteinsPlus_predict_binding_sites_v3"]
