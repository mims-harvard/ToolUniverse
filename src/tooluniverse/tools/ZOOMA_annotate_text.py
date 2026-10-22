"""
ZOOMA_annotate_text

Map free text to ontology terms with EBI ZOOMA and exact local pagination over the complete upstr...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ZOOMA_annotate_text(
    property_value: str,
    property_type: Optional[str] = None,
    ontologies: Optional[str | list[str]] = None,
    min_confidence: Optional[str] = None,
    max_results: Optional[int] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Map free text to ontology terms with EBI ZOOMA and exact local pagination over the complete upstr...

    Parameters
    ----------
    property_value : str
        Free text to annotate to ontology terms, e.g. 'bone marrow', 'asthma', 'Homo ...
    property_type : str
        Optional property-type hint that narrows the annotation context, e.g. 'diseas...
    ontologies : str | list[str]
        Ontology source filter as a comma-separated string or string array, e.g. 'efo...
    min_confidence : str
        Optional minimum confidence to keep, one of LOW, MEDIUM, GOOD, HIGH. Invalid ...
    max_results : int
        Legacy alias for limit. Maximum annotations on this page; defaults to 10.
    limit : int
        Maximum annotations on this local page, 1-1000. Takes precedence over max_res...
    offset : int
        Zero-based offset into the exact match set after min_confidence filtering. Co...
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
            "property_value": property_value,
            "property_type": property_type,
            "ontologies": ontologies,
            "min_confidence": min_confidence,
            "max_results": max_results,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ZOOMA_annotate_text",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ZOOMA_annotate_text"]
