"""
GPCRdb_get_ligands

Get ligands associated with a GPCR from GPCRdb. Returns ligand names, types (agonist/antagonist),...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GPCRdb_get_ligands(
    operation: Optional[str] = None,
    protein: Optional[str] = None,
    protein_id: Optional[str] = None,
    receptor_name: Optional[str] = None,
    protein_name: Optional[str] = None,
    type_: Optional[str] = None,
    ligand_type: Optional[str] = None,
    limit: Optional[int] = None,
    max_results: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get ligands associated with a GPCR from GPCRdb. Returns ligand names, types (agonist/antagonist),...

    Parameters
    ----------
    operation : str
        Operation type (fixed: get_ligands)
    protein : str
        Protein entry name (e.g., adrb2_human)
    protein_id : str
        Alias for protein parameter
    receptor_name : str
        Alias for protein. GPCRdb entry name (e.g., adrb2_human).
    protein_name : str
        Alias for protein. GPCRdb entry name (e.g., adrb2_human).
    type_ : str
        Ligand class filter (e.g., small molecule, peptide, antibody).
    ligand_type : str
        Alias for type. Ligand class filter (e.g., small molecule, peptide).
    limit : int
        Maximum number of ligands to return (default: all). Use to cap large result s...
    max_results : int
        Alias for limit. Maximum number of ligands to return.
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "operation": operation,
            "protein": protein,
            "protein_id": protein_id,
            "receptor_name": receptor_name,
            "protein_name": protein_name,
            "type": type_,
            "ligand_type": ligand_type,
            "limit": limit,
            "max_results": max_results,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GPCRdb_get_ligands",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GPCRdb_get_ligands"]
