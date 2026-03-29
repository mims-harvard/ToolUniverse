"""
OpenTargets_search_gwas_studies_by_disease

Search for GWAS studies associated with a disease or trait in Open Targets. Takes disease ontolog...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenTargets_search_gwas_studies_by_disease(
    diseaseIds: Optional[list[str]] = None,
    enableIndirect: Optional[bool] = True,
    disease_name: Optional[str] = None,
    disease: Optional[str] = None,
    trait: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search for GWAS studies associated with a disease or trait in Open Targets. Takes disease ontolog...

    Parameters
    ----------
    diseaseIds : list[str]
        Disease ontology IDs (e.g., ['MONDO_0005148'] for type 2 diabetes, ['MONDO_00...
    enableIndirect : bool
        Include studies for child disease terms (default true)
    disease_name : str
        Disease or trait name for auto-resolution (e.g., 'type 2 diabetes'). Resolved...
    disease : str
        Alias for disease_name.
    trait : str
        Alias for disease_name.
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
            "diseaseIds": diseaseIds,
            "enableIndirect": enableIndirect,
            "disease_name": disease_name,
            "disease": disease,
            "trait": trait,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OpenTargets_search_gwas_studies_by_disease",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenTargets_search_gwas_studies_by_disease"]
