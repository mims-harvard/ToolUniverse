"""
EuropePMC_get_fulltext

Fetch a PMC article's full text with deterministic fallbacks: Europe PMC fullTextXML → NCBI PMC O...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EuropePMC_get_fulltext(
    fulltext_xml_url: Optional[str] = None,
    pmcid: Optional[str] = None,
    source_db: Optional[str] = None,
    article_id: Optional[str] = None,
    output_format: Optional[str] = "text",
    include_raw: Optional[bool] = False,
    max_chars: Optional[int] = 200000,
    max_raw_chars: Optional[int] = 200000,
    timeout: Optional[int] = 30,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Optional[dict[str, Any]]:
    """
    Fetch a PMC article's full text with deterministic fallbacks: Europe PMC fullTextXML → NCBI PMC O...

    Parameters
    ----------
    fulltext_xml_url : str
        Direct Europe PMC fullTextXML URL (optional).
    pmcid : str
        PMC ID (e.g., 'PMC5234727' or '5234727').
    source_db : str
        Europe PMC source database (e.g., 'MED' or 'PMC'). Used with `article_id` to ...
    article_id : str
        Europe PMC article ID within `source_db` (e.g., PMID for source_db='MED').
    output_format : str
        Return 'text' (default; extracted plain text) or 'raw' (raw XML/HTML).
    include_raw : bool
        If true, also returns a bounded `raw` field (useful for downstream parsing).
    max_chars : int
        Hard cap on characters returned in `text` (or `content` when output_format='r...
    max_raw_chars : int
        Hard cap on characters returned in `raw` when include_raw=true.
    timeout : int
        HTTP timeout in seconds.
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    Optional[dict[str, Any]]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "fulltext_xml_url": fulltext_xml_url,
            "pmcid": pmcid,
            "source_db": source_db,
            "article_id": article_id,
            "output_format": output_format,
            "include_raw": include_raw,
            "max_chars": max_chars,
            "max_raw_chars": max_raw_chars,
            "timeout": timeout,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EuropePMC_get_fulltext",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EuropePMC_get_fulltext"]
