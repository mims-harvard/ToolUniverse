"""
VDJDB_get_antigen_specificity

Search VDJdb by epitope peptide sequence to find all TCRs with confirmed specificity for a given ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def VDJDB_get_antigen_specificity(
    operation: str,
    epitope: str,
    species: Optional[str | Any] = None,
    gene: Optional[str | Any] = None,
    mhc_class: Optional[str | Any] = None,
    min_score: Optional[int | Any] = None,
    page: Optional[int] = 0,
    page_size: Optional[int] = 25,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search VDJdb by epitope peptide sequence to find all TCRs with confirmed specificity for a given ...

    Parameters
    ----------
    operation : str
        Operation type
    epitope : str
        Epitope peptide sequence to search (e.g., 'GILGFVFTL' for Influenza M1, 'GLCT...
    species : str | Any
        Species filter: HomoSapiens, MusMusculus, or MacacaMulatta
    gene : str | Any
        TCR chain filter: TRA (alpha) or TRB (beta)
    mhc_class : str | Any
        MHC class filter: MHCI or MHCII
    min_score : int | Any
        Minimum VDJdb confidence score (0-3). Score 3 = highest confidence with multi...
    page : int
        Page number (0-indexed) for paginated results
    page_size : int
        Number of results per page (default: 25, max: 100)
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
    _args = {k: v for k, v in {
        "operation": operation,
                "epitope": epitope,
                "species": species,
                "gene": gene,
                "mhc_class": mhc_class,
                "min_score": min_score,
                "page": page,
                "page_size": page_size
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "VDJDB_get_antigen_specificity",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["VDJDB_get_antigen_specificity"]
