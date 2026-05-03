"""
fda_pharmacogenomic_biomarkers

Retrieve pharmacogenomic biomarkers from FDA drug labels. This tool fetches the Table of Pharmaco...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def fda_pharmacogenomic_biomarkers(
    drug_name: Optional[str] = None,
    biomarker: Optional[str] = None,
    limit: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Retrieve pharmacogenomic biomarkers from FDA drug labels. This tool fetches the Table of Pharmaco...

    Parameters
    ----------
    drug_name : str
        Filter by the name of the drug (e.g., 'Sivextro', 'Abacavir'). Case-insensiti...
    biomarker : str
        Filter by the specific biomarker (e.g., 'CYP2D6', 'HLA-B*5701'). Case-insensi...
    limit : int
        Maximum number of results to return.
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "drug_name": drug_name,
            "biomarker": biomarker,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "fda_pharmacogenomic_biomarkers",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["fda_pharmacogenomic_biomarkers"]
