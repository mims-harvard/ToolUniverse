"""
Metabolite_get_diseases

Get curated disease associations for a metabolite using CTD (Comparative Toxicogenomics Database)...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Metabolite_get_diseases(
    operation: Optional[str] = None,
    hmdb_id: Optional[str] = None,
    compound_name: Optional[str] = None,
    pubchem_cid: Optional[int | str] = None,
    limit: Optional[int] = 50,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get curated disease associations for a metabolite using CTD (Comparative Toxicogenomics Database)...

    Parameters
    ----------
    operation : str

    hmdb_id : str
        HMDB ID (e.g., HMDB0000122)
    compound_name : str
        Compound name (e.g., glucose, cholesterol)
    pubchem_cid : int | str
        PubChem CID (e.g., 5793)
    limit : int
        Maximum number of disease associations to return (default: 50)
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
            "hmdb_id": hmdb_id,
            "compound_name": compound_name,
            "pubchem_cid": pubchem_cid,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Metabolite_get_diseases",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Metabolite_get_diseases"]
