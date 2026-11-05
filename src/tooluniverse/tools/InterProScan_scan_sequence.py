"""
InterProScan_scan_sequence

Run InterProScan analysis on a protein sequence to predict domains, families, and functional site...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def InterProScan_scan_sequence(
    sequence: str,
    email: Optional[str] = None,
    title: Optional[str] = None,
    go_terms: Optional[bool] = True,
    pathways: Optional[bool] = True,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Run InterProScan analysis on a protein sequence to predict domains, families, and functional site...

    Parameters
    ----------
    sequence : str
        Protein sequence in single-letter amino acid code (e.g., 'MVLSPADKTNVKAAWGKVG...
    email : str
        Email for job notifications (optional)
    title : str
        Job title for tracking (optional)
    go_terms : bool
        Include GO term predictions
    pathways : bool
        Include pathway annotations
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
            "sequence": sequence,
            "email": email,
            "title": title,
            "go_terms": go_terms,
            "pathways": pathways,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "InterProScan_scan_sequence",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["InterProScan_scan_sequence"]
