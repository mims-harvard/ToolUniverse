"""
AllenBrain_get_structure_expression_values

Get quantified per-structure gene-expression values (StructureUnionize) for one Allen Mouse Brain...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def AllenBrain_get_structure_expression_values(
    section_data_set_id: int,
    include_structure: Optional[bool] = True,
    num_rows: Optional[int] = 50,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get quantified per-structure gene-expression values (StructureUnionize) for one Allen Mouse Brain...

    Parameters
    ----------
    section_data_set_id : int
        Allen Brain Atlas SectionDataSet (ISH experiment) ID. Get one from AllenBrain...
    include_structure : bool
        Whether to include the linked brain structure record (acronym, name, hierarch...
    num_rows : int
        Max per-structure rows to return. There are ~2400 structures per dataset. Def...
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
            "section_data_set_id": section_data_set_id,
            "include_structure": include_structure,
            "num_rows": num_rows,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "AllenBrain_get_structure_expression_values",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["AllenBrain_get_structure_expression_values"]
