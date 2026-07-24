"""
PGSCatalog_get_scores_by_trait

List the published polygenic scores (PGS) for a trait in the PGS Catalog, given its EFO/MONDO tra...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PGSCatalog_get_scores_by_trait(
    trait_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List the published polygenic scores (PGS) for a trait in the PGS Catalog, given its EFO/MONDO tra...

    Parameters
    ----------
    trait_id : str
        EFO or MONDO trait id, e.g. 'MONDO_0004989' (breast carcinoma) or 'EFO_000164...
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
    _args = {k: v for k, v in {"trait_id": trait_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "PGSCatalog_get_scores_by_trait",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PGSCatalog_get_scores_by_trait"]
