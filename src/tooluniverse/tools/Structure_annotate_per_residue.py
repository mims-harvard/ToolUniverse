"""
Structure_annotate_per_residue

Per-residue structural annotation from a PDB structure: which residues sit at a binding interface...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Structure_annotate_per_residue(
    operation: str,
    pdb_id: Optional[str] = None,
    pdb_content: Optional[str] = None,
    target_chain: Optional[str] = "A",
    partner_chains: Optional[list[str]] = None,
    ligand_resnames: Optional[list[str]] = None,
    distance_cutoff: Optional[float] = 5.0,
    core_rsa_cutoff: Optional[float] = 0.25,
    include_secondary_structure: Optional[bool] = False,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Per-residue structural annotation from a PDB structure: which residues sit at a binding interface...

    Parameters
    ----------
    operation : str
        Operation type
    pdb_id : str
        4-character PDB ID (e.g. '6VJJ'). If provided, the structure is downloaded fr...
    pdb_content : str
        Raw PDB file content (string). Use when the structure is local (e.g. AlphaFol...
    target_chain : str
        Chain ID of the protein to annotate (e.g. 'A').
    partner_chains : list[str]
        Chain IDs that define the binding partner(s). Used to compute the interface. ...
    ligand_resnames : list[str]
        Three-letter residue names of bound ligands to define the ligand pocket (e.g....
    distance_cutoff : float
        Distance cutoff in angstroms for interface and ligand-pocket classification.
    core_rsa_cutoff : float
        Relative solvent accessibility threshold below which a residue is classified ...
    include_secondary_structure : bool
        If true and pdb_id is provided, fetch per-residue secondary structure (helix/...
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
    if partner_chains is None:
        partner_chains = []
    if ligand_resnames is None:
        ligand_resnames = []
    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "operation": operation,
            "pdb_id": pdb_id,
            "pdb_content": pdb_content,
            "target_chain": target_chain,
            "partner_chains": partner_chains,
            "ligand_resnames": ligand_resnames,
            "distance_cutoff": distance_cutoff,
            "core_rsa_cutoff": core_rsa_cutoff,
            "include_secondary_structure": include_secondary_structure,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Structure_annotate_per_residue",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Structure_annotate_per_residue"]
