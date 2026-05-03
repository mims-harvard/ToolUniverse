"""
PDC_get_study_summary

Get detailed metadata for a specific cancer proteomics study from the NCI Proteomics Data Commons...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PDC_get_study_summary(
    operation: str,
    pdc_study_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed metadata for a specific cancer proteomics study from the NCI Proteomics Data Commons...

    Parameters
    ----------
    operation : str
        Operation type
    pdc_study_id : str
        PDC study accession number (e.g., 'PDC000127', 'PDC000120', 'PDC000173')
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
        for k, v in {"operation": operation, "pdc_study_id": pdc_study_id}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PDC_get_study_summary",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PDC_get_study_summary"]
