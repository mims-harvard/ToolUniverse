"""
GenCC_get_classifications

Get summary statistics of gene-disease validity classifications from GenCC (Gene Curation Coaliti...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GenCC_get_classifications(
    operation: str,
    submitter: Optional[str] = "",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get summary statistics of gene-disease validity classifications from GenCC (Gene Curation Coaliti...

    Parameters
    ----------
    operation : str
        Operation type (fixed: get_classifications)
    submitter : str
        Optional filter by submitting organization name (e.g., 'ClinGen', 'Ambry', 'G...
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

    return get_shared_client().run_one_function(
        {
            "name": "GenCC_get_classifications",
            "arguments": {"operation": operation, "submitter": submitter},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GenCC_get_classifications"]
