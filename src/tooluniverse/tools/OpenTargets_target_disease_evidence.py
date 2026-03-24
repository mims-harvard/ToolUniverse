"""
OpenTargets_target_disease_evidence

Explore IntOGen somatic driver evidence for a target-disease association. IMPORTANT: IntOGen only...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenTargets_target_disease_evidence(
    efoId: str,
    ensemblId: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Explore IntOGen somatic driver evidence for a target-disease association. IMPORTANT: IntOGen only...

    Parameters
    ----------
    efoId : str
        The efoId of a disease or phenotype.
    ensemblId : str
        The ensemblId of a target.
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
        for k, v in {"efoId": efoId, "ensemblId": ensemblId}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OpenTargets_target_disease_evidence",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenTargets_target_disease_evidence"]
