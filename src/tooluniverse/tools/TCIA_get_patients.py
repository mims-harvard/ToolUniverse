"""
TCIA_get_patients

List the patients (subjects) in a TCIA imaging collection. Returns patient-level fields not avail...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def TCIA_get_patients(
    Collection: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List the patients (subjects) in a TCIA imaging collection. Returns patient-level fields not avail...

    Parameters
    ----------
    Collection : str
        Collection name to list patients for (e.g., 'LIDC-IDRI', 'TCGA-GBM'). Omit to...
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
    _args = {k: v for k, v in {"Collection": Collection}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "TCIA_get_patients",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["TCIA_get_patients"]
