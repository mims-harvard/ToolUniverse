"""
humanbase_ppi_analysis

Retrieve tissue-specific protein-protein interactions and biological processes from HumanBase. Re...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def humanbase_ppi_analysis(
    gene_list: Optional[list[str]] = None,
    tissue: Optional[str] = "brain",
    max_node: Optional[int] = 10,
    interaction: Optional[str] = None,
    string_mode: Optional[bool] = True,
    genes: Optional[list[str]] = None,
    top_n: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> str:
    """
    Retrieve tissue-specific protein-protein interactions and biological processes from HumanBase. Re...

    Parameters
    ----------
    gene_list : list[str]
        List of gene names or symbols to analyze for protein-protein interactions. Th...
    tissue : str
        Tissue type for tissue-specific interactions. Use simple names like 'brain', ...
    max_node : int
        Maximum number of nodes to retrieve in the interaction network. Warning: the ...
    interaction : str
        Specific interaction type to filter by. Available types: 'co-expression', 'in...
    string_mode : bool
        Whether to return the result in string mode. If True, the result will be a st...
    genes : list[str]
        Alias for gene_list. List of gene symbols to analyze.
    top_n : int
        Alias for max_node. Maximum number of network nodes to retrieve.
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    str
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "gene_list": gene_list,
            "tissue": tissue,
            "max_node": max_node,
            "interaction": interaction,
            "string_mode": string_mode,
            "genes": genes,
            "top_n": top_n,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "humanbase_ppi_analysis",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["humanbase_ppi_analysis"]
