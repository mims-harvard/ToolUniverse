"""
VEuPathDB_get_gene_record

Retrieve the record for a single gene from a VEuPathDB pathogen-genome database by its gene ident...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def VEuPathDB_get_gene_record(
    gene_id: str,
    project: Optional[str] = None,
    attributes: Optional[list[str] | str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve the record for a single gene from a VEuPathDB pathogen-genome database by its gene ident...

    Parameters
    ----------
    gene_id : str
        Gene identifier / primary key (source_id) as used by VEuPathDB. Examples: 'PF...
    project : str
        VEuPathDB member site that owns the gene. One of: plasmodb (default), toxodb,...
    attributes : list[str] | str
        Optional list of gene attribute columns to return. Defaults to primary_key, p...
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
            "gene_id": gene_id,
            "project": project,
            "attributes": attributes,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "VEuPathDB_get_gene_record",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["VEuPathDB_get_gene_record"]
