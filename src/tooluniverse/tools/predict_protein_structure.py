"""
predict_protein_structure

Fold a protein sequence, with one model or every available one at once. Accepts a raw 1-letter se...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def predict_protein_structure(
    sequence: Optional[str] = None,
    sequences: Optional[list[str]] = None,
    uniprot: Optional[str] = None,
    gene: Optional[str] = None,
    ligand_smiles: Optional[str] = None,
    backend: Optional[str | list[str]] = None,
    list_models: Optional[bool] = None,
    include_notes: Optional[bool] = None,
    include_details: Optional[bool] = None,
    include_raw: Optional[bool] = None,
    max_workers: Optional[int] = None,
    reference_pdb_id: Optional[str] = None,
    reference_structure: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Fold a protein sequence, with one model or every available one at once. Accepts a raw 1-letter se...

    Parameters
    ----------
    sequence : str
        Protein sequence in 1-letter code. A FASTA record is accepted and its header ...
    sequences : list[str]
        Several chains, to fold a complex. Only some models support this.
    uniprot : str
        UniProt accession to fold; its canonical sequence is fetched.
    gene : str
        Gene symbol to fold; resolved to a reviewed UniProt entry first.
    ligand_smiles : str
        Ligand to co-fold with the receptor. Only Boltz-2 supports this.
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
    reference_pdb_id : str
        4-character PDB id of the experimental structure to score the prediction agai...
    reference_structure : str
        Reference coordinates as PDB text, as an alternative to reference_pdb_id.
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
            "sequence": sequence,
            "sequences": sequences,
            "uniprot": uniprot,
            "gene": gene,
            "ligand_smiles": ligand_smiles,
            "backend": backend,
            "list_models": list_models,
            "include_notes": include_notes,
            "include_details": include_details,
            "include_raw": include_raw,
            "max_workers": max_workers,
            "reference_pdb_id": reference_pdb_id,
            "reference_structure": reference_structure,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "predict_protein_structure",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["predict_protein_structure"]
