"""
EGA_get_study_datasets

List the dataset accessions belonging to one EGA study. Example: accession='EGAS00000000001' retu...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EGA_get_study_datasets(
    accession: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List the dataset accessions belonging to one EGA study. Example: accession='EGAS00000000001' retu...

    Parameters
    ----------
    accession : str
        EGA study accession, e.g. 'EGAS00000000001'.
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
    _args = {k: v for k, v in {"accession": accession}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "EGA_get_study_datasets",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EGA_get_study_datasets"]
