"""
StatPearls_get_chapter_section

Read a StatPearls clinical review chapter (NCBI Bookshelf NBK430685). Give the chapter as the cha...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def StatPearls_get_chapter_section(
    chapter: str,
    section: Optional[str] = None,
    page: Optional[int] = 1,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Read a StatPearls clinical review chapter (NCBI Bookshelf NBK430685). Give the chapter as the cha...

    Parameters
    ----------
    chapter : str
        chapter_id from StatPearls_search (e.g. 'article-17465') or the chapter title...
    section : str
        Optional section heading to read, e.g. 'Administration', 'Adverse Effects', '...
    page : int
        Page of a long section to return (default 1).
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
        for k, v in {"chapter": chapter, "section": section, "page": page}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "StatPearls_get_chapter_section",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["StatPearls_get_chapter_section"]
