"""
COD_search_structures

Search the Crystallography Open Database (COD) for crystal structures by chemical formula, elemen...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def COD_search_structures(
    query: Optional[str] = None,
    text: Optional[str] = None,
    formula: Optional[str] = None,
    el1: Optional[str] = None,
    el2: Optional[str] = None,
    el3: Optional[str] = None,
    nel: Optional[str] = None,
    commonname: Optional[str] = None,
    mineral: Optional[str] = None,
    spacegroup: Optional[str] = None,
    sg: Optional[str] = None,
    sgNumber: Optional[str] = None,
    max_results: Optional[int] = None,
    results: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the Crystallography Open Database (COD) for crystal structures by chemical formula, elemen...

    Parameters
    ----------
    query : str
        Alias for 'text'. Free text search across titles, keywords, and compound name...
    text : str
        Free text search across titles, keywords, and compound names. Examples: 'aspi...
    formula : str
        Chemical formula to search (use spaces between elements). Examples: 'Fe2 O3',...
    el1 : str
        First required element (chemical symbol). Examples: 'Cu', 'Fe', 'Si', 'C', 'N'
    el2 : str
        Second required element (chemical symbol)
    el3 : str
        Third required element (chemical symbol)
    nel : str
        Number of distinct elements in formula (e.g., '2' for binary compounds, '3' f...
    commonname : str
        Common/trivial name search (partial match). Examples: 'quartz', 'perovskite',...
    mineral : str
        Mineral name search (partial match). Examples: 'calcite', 'feldspar', 'pyrite...
    spacegroup : str
        Alias for 'sg'. Space group symbol (Hermann-Mauguin notation). Examples: 'P 2...
    sg : str
        Space group symbol (Hermann-Mauguin notation). Examples: 'P 21/c', 'Fm -3 m',...
    sgNumber : str
        Space group number (1-230). Examples: '225' (Fm-3m, FCC metals), '62' (Pnma, ...
    max_results : int
        Alias for 'results'. Maximum number of results to return (default 100, use sm...
    results : int
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

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "query": query,
            "text": text,
            "formula": formula,
            "el1": el1,
            "el2": el2,
            "el3": el3,
            "nel": nel,
            "commonname": commonname,
            "mineral": mineral,
            "spacegroup": spacegroup,
            "sg": sg,
            "sgNumber": sgNumber,
            "max_results": max_results,
            "results": results,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "COD_search_structures",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["COD_search_structures"]
