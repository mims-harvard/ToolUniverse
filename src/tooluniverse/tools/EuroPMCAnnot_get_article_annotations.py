"""
EuroPMCAnnot_get_article_annotations

Get text-mined annotations from a scientific article using the Europe PMC Annotations API. Return...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EuroPMCAnnot_get_article_annotations(
    article_id: str,
    annotation_type: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get text-mined annotations from a scientific article using the Europe PMC Annotations API. Return...

    Parameters
    ----------
    article_id : str
        Article identifier in format 'PMC:PMCXXXXXXX' or 'MED:PMID'. Examples: 'PMC:P...
    annotation_type : str | Any
        Filter by annotation type: 'Chemicals', 'Organisms', 'Gene Ontology', 'Diseas...
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
            "article_id": article_id,
            "annotation_type": annotation_type,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EuroPMCAnnot_get_article_annotations",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EuroPMCAnnot_get_article_annotations"]
