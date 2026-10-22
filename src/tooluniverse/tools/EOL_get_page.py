"""
EOL_get_page

Get detailed species/taxon information from an Encyclopedia of Life (EOL) page. Common names, syn...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EOL_get_page(
    page_id: int,
    images_per_page: Optional[int] = 3,
    texts_per_page: Optional[int] = 2,
    common_names: Optional[bool] = True,
    synonyms: Optional[bool] = True,
    details: Optional[bool] = True,
    common_name_limit: Optional[int] = 20,
    common_name_offset: Optional[int] = 0,
    synonym_limit: Optional[int] = 20,
    synonym_offset: Optional[int] = 0,
    classification_limit: Optional[int] = 15,
    classification_offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed species/taxon information from an Encyclopedia of Life (EOL) page. Common names, syn...

    Parameters
    ----------
    page_id : int
        EOL page identifier. Get this from EOL_search_species. Examples: 327955 (Homo...
    images_per_page : int
        Number of image data objects to return (0-75).
    texts_per_page : int
        Number of text description objects to return (0-75).
    common_names : bool
        Include vernacular/common names in multiple languages.
    synonyms : bool
        Include taxonomic synonyms.
    details : bool
        Include detailed data object information (media, descriptions).
    common_name_limit : int
        Maximum common names to return on this page.
    common_name_offset : int
        Zero-based offset into all common names.
    synonym_limit : int
        Maximum taxonomic synonyms to return on this page.
    synonym_offset : int
        Zero-based offset into all taxonomic synonyms.
    classification_limit : int
        Maximum source classifications to return on this page.
    classification_offset : int
        Zero-based offset into all source classifications.
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
            "page_id": page_id,
            "images_per_page": images_per_page,
            "texts_per_page": texts_per_page,
            "common_names": common_names,
            "synonyms": synonyms,
            "details": details,
            "common_name_limit": common_name_limit,
            "common_name_offset": common_name_offset,
            "synonym_limit": synonym_limit,
            "synonym_offset": synonym_offset,
            "classification_limit": classification_limit,
            "classification_offset": classification_offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EOL_get_page",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EOL_get_page"]
