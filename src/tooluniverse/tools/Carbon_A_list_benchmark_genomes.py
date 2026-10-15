"""
Carbon_A_list_benchmark_genomes

List the eukaryotic genomes in the Carbon-A evaluation collection, the benchmark set published wi...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Carbon_A_list_benchmark_genomes(
    split: Optional[str] = "all",
    organism_contains: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    List the eukaryotic genomes in the Carbon-A evaluation collection, the benchmark set published wi...

    Parameters
    ----------
    split : str
        Restrict to one eval/ subdirectory. These are the publisher's own labels, rep...
    organism_contains : str
        Case-insensitive substring of the organism name, for example 'Saccharomyces',...
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
        for k, v in {"split": split, "organism_contains": organism_contains}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Carbon_A_list_benchmark_genomes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Carbon_A_list_benchmark_genomes"]
