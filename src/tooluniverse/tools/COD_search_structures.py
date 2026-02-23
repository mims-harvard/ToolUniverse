"""
COD_search_structures

Search the Crystallography Open Database (COD) for crystal structures by chemical formula, elemen...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def COD_search_structures(
    text: Optional[str | Any] = None,
    formula: Optional[str | Any] = None,
    el1: Optional[str | Any] = None,
    el2: Optional[str | Any] = None,
    el3: Optional[str | Any] = None,
    nel: Optional[str | Any] = None,
    commonname: Optional[str | Any] = None,
    mineral: Optional[str | Any] = None,
    sg: Optional[str | Any] = None,
    sgNumber: Optional[str | Any] = None,
    results: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the Crystallography Open Database (COD) for crystal structures by chemical formula, elemen...

    Parameters
    ----------
    text : str | Any
        Free text search across titles, keywords, and compound names. Examples: 'aspi...
    formula : str | Any
        Chemical formula to search (use spaces between elements). Examples: 'Fe2 O3',...
    el1 : str | Any
        First required element (chemical symbol). Examples: 'Cu', 'Fe', 'Si', 'C', 'N'
    el2 : str | Any
        Second required element (chemical symbol)
    el3 : str | Any
        Third required element (chemical symbol)
    nel : str | Any
        Number of distinct elements in formula (e.g., '2' for binary compounds, '3' f...
    commonname : str | Any
        Common/trivial name search (partial match). Examples: 'quartz', 'perovskite',...
    mineral : str | Any
        Mineral name search (partial match). Examples: 'calcite', 'feldspar', 'pyrite...
    sg : str | Any
        Space group symbol (Hermann-Mauguin notation). Examples: 'P 21/c', 'Fm -3 m',...
    sgNumber : str | Any
        Space group number (1-230). Examples: '225' (Fm-3m, FCC metals), '62' (Pnma, ...
    results : int | Any
        Maximum number of results to return (default 100, use smaller values for spee...
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
            "name": "COD_search_structures",
            "arguments": {
                "text": text,
                "formula": formula,
                "el1": el1,
                "el2": el2,
                "el3": el3,
                "nel": nel,
                "commonname": commonname,
                "mineral": mineral,
                "sg": sg,
                "sgNumber": sgNumber,
                "results": results,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["COD_search_structures"]
