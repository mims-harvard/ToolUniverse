"""
ZOOMA_annotate_text

Map a free-text term (e.g. a sample attribute, phenotype, organism name, anatomical part, or dise...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ZOOMA_annotate_text(
    property_value: str,
    property_type: Optional[str] = None,
    ontologies: Optional[str] = None,
    min_confidence: Optional[str] = None,
    max_results: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Map a free-text term (e.g. a sample attribute, phenotype, organism name, anatomical part, or dise...

    Parameters
    ----------
    property_value : str
        Free text to annotate to ontology terms, e.g. 'bone marrow', 'asthma', 'Homo ...
    property_type : str
        Optional property-type hint that narrows the annotation context, e.g. 'diseas...
    ontologies : str
        Optional comma-separated ontology source filter restricting matches to these ...
    min_confidence : str
        Optional minimum confidence to keep, one of 'LOW', 'MEDIUM', 'GOOD', 'HIGH'. ...
    max_results : int
        Maximum number of annotations to return (default 10). ZOOMA can return 100+ f...
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
            "property_value": property_value,
            "property_type": property_type,
            "ontologies": ontologies,
            "min_confidence": min_confidence,
            "max_results": max_results,
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
