"""
Orphanet_get_phenotypes

Get HPO (Human Phenotype Ontology) phenotypes associated with a rare disease from Orphanet. Retur...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Orphanet_get_phenotypes(
    operation: Optional[str] = None,
    orpha_code: Optional[str | int] = None,
    orpha_id: Optional[str | int] = None,
    orphacode: Optional[int | str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get HPO (Human Phenotype Ontology) phenotypes associated with a rare disease from Orphanet. Retur...

    Parameters
    ----------
    operation : str
        Operation type (fixed: get_phenotypes)
    orpha_code : str | int
        Orphanet ORPHA code (e.g., 558 for Marfan, 586 for Cystic Fibrosis)
    orpha_id : str | int
        Alias for orpha_code. Orphanet ORPHA code (e.g., 558 for Marfan)
    orphacode : int | str
        Alias for orpha_code (the Orphanet disease code).
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
            "orpha_code": orpha_code,
            "orpha_id": orpha_id,
            "orphacode": orphacode,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Orphanet_get_phenotypes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Orphanet_get_phenotypes"]
