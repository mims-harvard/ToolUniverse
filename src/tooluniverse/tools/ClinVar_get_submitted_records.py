"""
ClinVar_get_submitted_records

Retrieve the individual per-submitter assertions (SCV / ClinicalAssertion records) for a ClinVar ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ClinVar_get_submitted_records(
    variant_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve the individual per-submitter assertions (SCV / ClinicalAssertion records) for a ClinVar ...

    Parameters
    ----------
    variant_id : str
        ClinVar variant identifier. Accepts a VCV accession (e.g. 'VCV000013961') OR ...
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
    _args = {k: v for k, v in {"variant_id": variant_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "ClinVar_get_submitted_records",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ClinVar_get_submitted_records"]
