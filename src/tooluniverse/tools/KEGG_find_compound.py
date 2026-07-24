"""
KEGG_find_compound

Search the KEGG COMPOUND database for candidate metabolites by exact (monoisotopic) mass, average...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def KEGG_find_compound(
    exact_mass: Optional[str | float] = None,
    mol_weight: Optional[str | float] = None,
    formula: Optional[str] = None,
    name: Optional[str] = None,
    query: Optional[str] = None,
    max_results: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the KEGG COMPOUND database for candidate metabolites by exact (monoisotopic) mass, average...

    Parameters
    ----------
    exact_mass : str | float
        Monoisotopic / exact mass to search by. Single value (e.g. 174.05) or a range...
    mol_weight : str | float
        Average molecular weight to search by. Single value or a range as 'low-high' ...
    formula : str
        Molecular formula to search by, e.g. 'C6H12O6'. Mutually exclusive with exact...
    name : str
        Compound name or keyword to search by, e.g. 'caffeine', 'glucose'. Mutually e...
    query : str
        Alias for 'name': compound name or keyword to search by.
    max_results : int
        Optional cap on the number of returned candidate compounds.
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
            "exact_mass": exact_mass,
            "mol_weight": mol_weight,
            "formula": formula,
            "name": name,
            "query": query,
            "max_results": max_results,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "KEGG_find_compound",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["KEGG_find_compound"]
