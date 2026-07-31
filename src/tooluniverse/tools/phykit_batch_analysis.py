"""
phykit_batch_analysis

Run PhyKIT phylogenetics functions (treeness, saturation, dvmc, long_branch_score, total_tree_len...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def phykit_batch_analysis(
    operation: str,
    function: Optional[str] = None,
    file: Optional[str] = None,
    directory: Optional[str] = None,
    extension: Optional[str] = None,
    tree_directory: Optional[str] = None,
    tree_extension: Optional[str] = None,
    per_tree_stat: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Run PhyKIT phylogenetics functions (treeness, saturation, dvmc, long_branch_score, total_tree_len...

    Parameters
    ----------
    operation : str
        single: one file, batch: all files in directory, gap_percentage: compute gap ...
    function : str
        PhyKIT function to run
    file : str
        Path to single tree/alignment file (for operation=single)
    directory : str
        Directory containing tree/alignment files (for operation=batch or gap_percent...
    extension : str
        File extension to match (default: .treefile for trees, .fa for alignments)
    tree_directory : str
        Directory with paired tree files (for saturation function)
    tree_extension : str
        Tree file extension (default: .treefile)
    per_tree_stat : str
        How to summarize per-tree values for long_branch_score (default: mean)
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
            "operation": operation,
            "function": function,
            "file": file,
            "directory": directory,
            "extension": extension,
            "tree_directory": tree_directory,
            "tree_extension": tree_extension,
            "per_tree_stat": per_tree_stat,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "phykit_batch_analysis",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["phykit_batch_analysis"]
