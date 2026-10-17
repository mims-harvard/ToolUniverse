"""
predict_binding_affinity

Dock or score one protein-ligand pair, with one model or all of them. Give 'ligand_smiles' (or a ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def predict_binding_affinity(
    ligand_smiles: Optional[str] = None,
    ligand: Optional[str] = None,
    pdb_id: Optional[str] = None,
    protein_sequence: Optional[str] = None,
    uniprot: Optional[str] = None,
    target: Optional[str] = None,
    backend: Optional[str | list[str]] = None,
    list_models: Optional[bool] = None,
    include_notes: Optional[bool] = None,
    include_details: Optional[bool] = None,
    include_raw: Optional[bool] = None,
    max_workers: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Dock or score one protein-ligand pair, with one model or all of them. Give 'ligand_smiles' (or a ...

    Parameters
    ----------
    ligand_smiles : str
        Ligand as SMILES.
    ligand : str
        Ligand name, resolved to SMILES via PubChem.
    pdb_id : str
        4-character PDB id of the receptor (required by structure-based docking).
    protein_sequence : str
        Receptor sequence, for models that need no experimental structure.
    uniprot : str
        UniProt accession of the receptor.
    target : str
        Target gene symbol.
    backend : str | list[str]
        Which model(s) to run. Omit or use 'all' to run every applicable model and ge...
    list_models : bool
        Return the catalogue of models for this task -- id, units, direction, API key...
    include_notes : bool
        With list_models, include per-model caveats. Default true.
    include_details : bool
        Include each model's full canonical record, not just the summary table. Defau...
    include_raw : bool
        Keep bulky payloads (structure coordinates, docking poses) in the reply. Defa...
    max_workers : int
        Models to run concurrently. Default 6.
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
            "ligand_smiles": ligand_smiles,
            "ligand": ligand,
            "pdb_id": pdb_id,
            "protein_sequence": protein_sequence,
            "uniprot": uniprot,
            "target": target,
            "backend": backend,
            "list_models": list_models,
            "include_notes": include_notes,
            "include_details": include_details,
            "include_raw": include_raw,
            "max_workers": max_workers,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "predict_binding_affinity",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["predict_binding_affinity"]
