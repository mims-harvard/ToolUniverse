"""
ClinVar_get_clinical_significance

Get clinical significance information for a variant from ClinVar. Returns pathogenicity classific...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ClinVar_get_clinical_significance(
    variant_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get clinical significance information for a variant from ClinVar. Returns pathogenicity classific...

    Parameters
    ----------
    variant_id : str
        ClinVar variant ID (e.g., '12345', '123456')
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
    _args = {k: v for k, v in {"variant_id": variant_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "ClinVar_get_clinical_significance",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ClinVar_get_clinical_significance"]
