"""
EVA_list_studies

List all variant studies available in the European Variation Archive (EVA) for a given species. R...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EVA_list_studies(
    species: Optional[str] = 'hsapiens_grch38',
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List all variant studies available in the European Variation Archive (EVA) for a given species. R...

    Parameters
    ----------
    species : str
        Species and assembly (e.g., 'hsapiens_grch38', 'hsapiens_grch37', 'mmusculus_...
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
    _args = {k: v for k, v in {
        "species": species
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "EVA_list_studies",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["EVA_list_studies"]
