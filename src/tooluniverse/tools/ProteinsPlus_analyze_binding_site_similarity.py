"""
ProteinsPlus_analyze_binding_site_similarity

Analyze binding site similarity and generate structural ensembles using SIENA (Structural Interac...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ProteinsPlus_analyze_binding_site_similarity(
    pdb_id: str,
    mode: str,
    ligand: Optional[str] = None,
    pocket: Optional[str] = None,
    fragment_length: Optional[int] = None,
    flexibility_sensitivity: Optional[float] = None,
    site_radius: Optional[float] = None,
    minimal_site_identity: Optional[float] = None,
    minimal_site_coverage: Optional[float] = None,
    maximum_mutations: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Analyze binding site similarity and generate structural ensembles using SIENA (Structural Interac...

    Parameters
    ----------
    pdb_id : str
        PDB identifier (e.g., '1KZK', '2OZR', '4HHB'). Required.
    mode : str
        Analysis mode: 'flexibility_analysis' (compare protein conformations), 'docki...
    ligand : str
        Ligand identifier in format 'residue_name_residue_chain_residue_number' (e.g....
    pocket : str
        Pocket definition for analysis (alternative to ligand). Example: Define custo...
    fragment_length : int
        Fragment length for analysis (3-15). Default: 9. Longer fragments = more spec...
    flexibility_sensitivity : float
        Sensitivity for flexibility detection (0.0-1.0). Default: 0.5. Higher = more ...
    site_radius : float
        Radius around ligand to define binding site (3-15 Angstroms). Requires ligand...
    minimal_site_identity : float
        Minimum binding site sequence identity threshold (0.3-1.0). Default: 0.6. Hig...
    minimal_site_coverage : float
        Minimum binding site coverage required (0.3-1.0). Default: 0.8. Higher = more...
    maximum_mutations : int
        Maximum number of mutations allowed in mutation analysis mode (0-10). Default...
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
            "mode": mode,
            "ligand": ligand,
            "pocket": pocket,
            "fragment_length": fragment_length,
            "flexibility_sensitivity": flexibility_sensitivity,
            "site_radius": site_radius,
            "minimal_site_identity": minimal_site_identity,
            "minimal_site_coverage": minimal_site_coverage,
            "maximum_mutations": maximum_mutations,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ProteinsPlus_analyze_binding_site_similarity",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ProteinsPlus_analyze_binding_site_similarity"]
