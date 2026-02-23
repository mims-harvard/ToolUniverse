"""
PubTator3_get_annotations

Extract biomedical entity annotations from PubMed articles using NCBI PubTator3. Given one or mor...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PubTator3_get_annotations(
    pmids: str,
    concepts: Optional[str] = "gene,disease,chemical,species,mutation,cellline",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Extract biomedical entity annotations from PubMed articles using NCBI PubTator3. Given one or mor...

    Parameters
    ----------
    pmids : str
        Comma-separated PubMed IDs (e.g., '33205991', '33205991,34234088'). Maximum ~...
    concepts : str
        Comma-separated entity types to extract: gene, disease, chemical, species, mu...
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
            "name": "PubTator3_get_annotations",
            "arguments": {"pmids": pmids, "concepts": concepts},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PubTator3_get_annotations"]
