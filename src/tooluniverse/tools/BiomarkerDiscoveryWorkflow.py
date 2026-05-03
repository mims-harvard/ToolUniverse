"""
BiomarkerDiscoveryWorkflow

Discover and validate biomarkers for a specific disease condition using literature analysis, expr...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BiomarkerDiscoveryWorkflow(
    disease_condition: str,
    sample_type: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Discover and validate biomarkers for a specific disease condition using literature analysis, expr...

    Parameters
    ----------
    disease_condition : str
        The disease condition to discover biomarkers for (e.g., 'breast cancer', 'Alz...
    sample_type : str
        The type of sample to analyze (e.g., 'blood', 'tissue', 'plasma')
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
            "disease_condition": disease_condition,
            "sample_type": sample_type,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "BiomarkerDiscoveryWorkflow",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BiomarkerDiscoveryWorkflow"]
