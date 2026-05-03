"""
SYNERGxDB_search_combos

Search drug combination synergy scores in SYNERGxDB. Returns synergy metrics (Bliss, Loewe, HSA, ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SYNERGxDB_search_combos(
    operation: Optional[str] = None,
    drug_id_1: Optional[int | Any] = None,
    drug_name_1: Optional[str | Any] = None,
    drug_id_2: Optional[int | Any] = None,
    drug_name_2: Optional[str | Any] = None,
    sample: Optional[str | Any] = None,
    dataset: Optional[int | str | Any] = None,
    page: Optional[int] = 1,
    per_page: Optional[int] = 20,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search drug combination synergy scores in SYNERGxDB. Returns synergy metrics (Bliss, Loewe, HSA, ...

    Parameters
    ----------
    operation : str
        Operation type
    drug_id_1 : int | Any
        SYNERGxDB drug ID for drug A. Use SYNERGxDB_list_drugs to find IDs. Examples:...
    drug_name_1 : str | Any
        Drug name for drug A — triggers automatic SYNERGxDB ID lookup (e.g., 'gemcita...
    drug_id_2 : int | Any
        SYNERGxDB drug ID for drug B. Examples: 97 (Topotecan), 34 (Erlotinib), 24 (D...
    drug_name_2 : str | Any
        Drug name for drug B — triggers automatic SYNERGxDB ID lookup (e.g., 'erlotin...
    sample : str | Any
        Cell line ID (integer as string) or tissue name. Valid tissue names: 'colorec...
    dataset : int | str | Any
        Dataset source ID (integer) or name (string). Examples: 2 or 'NCI-ALMANAC', 1...
    page : int
        Page number for paginated results (default: 1)
    per_page : int
        Results per page (default: 20, max: 500)
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "operation": operation,
            "drug_id_1": drug_id_1,
            "drug_name_1": drug_name_1,
            "drug_id_2": drug_id_2,
            "drug_name_2": drug_name_2,
            "sample": sample,
            "dataset": dataset,
            "page": page,
            "per_page": per_page,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "SYNERGxDB_search_combos",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SYNERGxDB_search_combos"]
