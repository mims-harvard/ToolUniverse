"""
PharmGKB_get_drug_label_annotations

Get regulatory drug-label pharmacogenomic annotations from PharmGKB/ClinPGx. By default lists FDA...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PharmGKB_get_drug_label_annotations(
    label_id: Optional[str] = None,
    source: Optional[str] = None,
    limit: Optional[int] = None,
    id: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get regulatory drug-label pharmacogenomic annotations from PharmGKB/ClinPGx. By default lists FDA...

    Parameters
    ----------
    label_id : str
        PharmGKB Label Annotation ID (e.g., 'PA166114907' for the FDA bosutinib label...
    source : str
        Regulatory agency for the listing mode. One of FDA, EMA, HCSC, PMDA. Defaults...
    limit : int
        Maximum number of label annotations to return in listing mode (default 50, ma...
    id : str
        Alias for label_id.
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
            "label_id": label_id,
            "source": source,
            "limit": limit,
            "id": id,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PharmGKB_get_drug_label_annotations",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PharmGKB_get_drug_label_annotations"]
