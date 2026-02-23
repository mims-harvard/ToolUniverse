"""
NCCN_list_patient_guidelines

List all NCCN (National Comprehensive Cancer Network) Guidelines for Patients available on nccn.o...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NCCN_list_patient_guidelines(
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List all NCCN (National Comprehensive Cancer Network) Guidelines for Patients available on nccn.o...

    Parameters
    ----------
    No parameters
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

    return get_shared_client().run_one_function(
        {"name": "NCCN_list_patient_guidelines", "arguments": {}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NCCN_list_patient_guidelines"]
