"""
BioPortal_annotate_text

Annotate biomedical text with ontology terms using BioPortal's Annotator (named entity recognitio...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BioPortal_annotate_text(
    text: str,
    ontologies: Optional[str | Any] = None,
    longest_only: Optional[bool | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Annotate biomedical text with ontology terms using BioPortal's Annotator (named entity recognitio...

    Parameters
    ----------
    text : str
        Biomedical text to annotate. Can be a sentence, abstract, or clinical note. M...
    ontologies : str | Any
        Comma-separated ontology acronyms to restrict annotation. If null, uses all o...
    longest_only : bool | Any
        If true (default), only return longest matching spans. Set false for all poss...
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
        {
            "name": "BioPortal_annotate_text",
            "arguments": {
                "text": text,
                "ontologies": ontologies,
                "longest_only": longest_only,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BioPortal_annotate_text"]
