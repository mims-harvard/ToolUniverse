"""
ChEMBL_get_drug_mechanisms

Get mechanisms of action for a drug by ChEMBL drug ID or drug name. Accepts drug_chembl_id (e.g.,...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ChEMBL_get_drug_mechanisms(
    limit: Optional[int] = 20,
    offset: Optional[int] = 0,
    drug_chembl_id: Optional[str] = None,
    drug_name: Optional[str] = None,
    molecule_chembl_id: Optional[str] = None,
    chembl_id: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get mechanisms of action for a drug by ChEMBL drug ID or drug name. Accepts drug_chembl_id (e.g.,...

    Parameters
    ----------
    limit : int

    offset : int

    drug_chembl_id : str
        ChEMBL drug/molecule ID (e.g., "CHEMBL1201581" for adalimumab, "CHEMBL4535757...
    drug_name : str
        Drug name for automatic ChEMBL ID lookup (e.g., "trastuzumab", "lapatinib", "...
    molecule_chembl_id : str
        Alias for drug_chembl_id. ChEMBL molecule ID (e.g., "CHEMBL25" for aspirin).
    chembl_id : str
        Alias for drug_chembl_id. ChEMBL ID (e.g., "CHEMBL3301622").
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
            "limit": limit,
            "offset": offset,
            "drug_chembl_id": drug_chembl_id,
            "drug_name": drug_name,
            "molecule_chembl_id": molecule_chembl_id,
            "chembl_id": chembl_id,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ChEMBL_get_drug_mechanisms",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ChEMBL_get_drug_mechanisms"]
