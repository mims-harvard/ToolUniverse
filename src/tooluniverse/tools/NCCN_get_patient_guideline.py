"""
NCCN_get_patient_guideline

Fetch content from a specific NCCN Guidelines for Patients page. Takes a URL obtained from NCCN_l...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NCCN_get_patient_guideline(
    url: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Fetch content from a specific NCCN Guidelines for Patients page. Takes a URL obtained from NCCN_l...

    Parameters
    ----------
    url : str
        URL of the NCCN patient guideline page (from NCCN_list_patient_guidelines out...
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
    _args = {k: v for k, v in {"url": url}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "NCCN_get_patient_guideline",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NCCN_get_patient_guideline"]
