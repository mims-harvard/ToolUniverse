"""
EPMC_get_text_mined_annotations

Get all text-mined annotations from a biomedical article via Europe PMC. Returns gene/protein men...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EPMC_get_text_mined_annotations(
    pmid: Optional[str] = None,
    pmcid: Optional[str] = None,
    annotation_type: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get all text-mined annotations from a biomedical article via Europe PMC. Returns gene/protein men...

    Parameters
    ----------
    pmid : str
        PubMed ID (e.g., '33332779'). Either pmid or pmcid is required.
    pmcid : str
        PubMed Central ID (e.g., 'PMC7781101'). Alternative to pmid.
    annotation_type : str
        Filter by annotation type. Options: 'Gene_Proteins', 'Diseases', 'Chemicals',...
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
            "pmid": pmid,
            "pmcid": pmcid,
            "annotation_type": annotation_type,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EPMC_get_text_mined_annotations",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EPMC_get_text_mined_annotations"]
