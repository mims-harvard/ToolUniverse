"""
EuropePMC_get_full_text

Retrieve and parse full-text XML from Europe PMC into structured sections. Returns title, abstrac...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EuropePMC_get_full_text(
    pmcid: Optional[str] = None,
    pmid: Optional[str] = None,
    max_section_chars: Optional[int] = 50000,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve and parse full-text XML from Europe PMC into structured sections. Returns title, abstrac...

    Parameters
    ----------
    pmcid : str
        PubMed Central ID (e.g., 'PMC7096075' or '7096075'). Preferred identifier.
    pmid : str
        PubMed ID (e.g., '32226684'). Will be auto-resolved to a PMC ID via Europe PM...
    max_section_chars : int
        Maximum characters per section in the output. Longer sections are truncated.
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
            "pmcid": pmcid,
            "pmid": pmid,
            "max_section_chars": max_section_chars,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EuropePMC_get_full_text",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EuropePMC_get_full_text"]
