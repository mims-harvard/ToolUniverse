"""
MedicalLiteratureReviewer

Conducts systematic reviews of medical literature on specific topics. Synthesizes findings from m...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MedicalLiteratureReviewer(
    research_topic: str,
    literature_content: str,
    focus_area: str,
    study_types: str,
    quality_level: str,
    review_scope: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Conducts systematic reviews of medical literature on specific topics. Synthesizes findings from m...

    Parameters
    ----------
    research_topic : str
        The specific medical/research topic for literature review (e.g., 'efficacy of...
    literature_content : str
        The literature content, abstracts, full studies, or research papers to review...
    focus_area : str
        Primary focus area for the review (e.g., 'therapeutic efficacy', 'safety prof...
    study_types : str
        Types of studies to prioritize in the analysis (e.g., 'randomized controlled ...
    quality_level : str
        Minimum evidence quality level to include (e.g., 'high quality only', 'modera...
    review_scope : str
        Scope of the review (e.g., 'comprehensive systematic review', 'rapid review',...
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
            "name": "MedicalLiteratureReviewer",
            "arguments": {
                "research_topic": research_topic,
                "literature_content": literature_content,
                "focus_area": focus_area,
                "study_types": study_types,
                "quality_level": quality_level,
                "review_scope": review_scope,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MedicalLiteratureReviewer"]
