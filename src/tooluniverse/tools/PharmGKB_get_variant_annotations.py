"""
PharmGKB_get_variant_annotations

Get variant-level literature annotations from PharmGKB/ClinPGx, filtered by gene or chemical Phar...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PharmGKB_get_variant_annotations(
    gene_id: Optional[str] = None,
    chemical_id: Optional[str] = None,
    drug_id: Optional[str] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get variant-level literature annotations from PharmGKB/ClinPGx, filtered by gene or chemical Phar...

    Parameters
    ----------
    gene_id : str
        PharmGKB Gene Accession ID (e.g., 'PA126' for CYP2C9). Queried via location.g...
    chemical_id : str
        PharmGKB Chemical/drug Accession ID (e.g., 'PA451906' for warfarin). Queried ...
    drug_id : str
        Alias for chemical_id.
    limit : int
        Maximum number of variant annotations to return (default 50, max 500). CYP2C9...
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
            "gene_id": gene_id,
            "chemical_id": chemical_id,
            "drug_id": drug_id,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PharmGKB_get_variant_annotations",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PharmGKB_get_variant_annotations"]
