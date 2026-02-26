"""
MetaboAnalyst_biomarker_enrichment

Find statistically enriched metabolite sets (biomarker panels) from a list of metabolites. Tests ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MetaboAnalyst_biomarker_enrichment(
    metabolites: list[str],
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Find statistically enriched metabolite sets (biomarker panels) from a list of metabolites. Tests ...

    Parameters
    ----------
    metabolites : list[str]
        List of metabolite names to test for set enrichment. Example: ['glucose', 'py...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    return get_shared_client().run_one_function(
        {
            "name": "MetaboAnalyst_biomarker_enrichment",
            "arguments": {"metabolites": metabolites},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MetaboAnalyst_biomarker_enrichment"]
