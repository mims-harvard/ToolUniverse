"""
Eurostat_get_dataset

Retrieve statistical data from Eurostat (EU statistical office) for a specific dataset and filter...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Eurostat_get_dataset(
    datasetCode: str,
    geo: Optional[str | Any] = None,
    unit: Optional[str | Any] = None,
    na_item: Optional[str | Any] = None,
    time: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve statistical data from Eurostat (EU statistical office) for a specific dataset and filter...

    Parameters
    ----------
    datasetCode : str
        Eurostat dataset code. Examples: 'demo_pjan' (population by age/sex), 'nama_1...
    geo : str | Any
        Country/region code filter. EU country codes: DE (Germany), FR (France), IT (...
    unit : str | Any
        Unit of measurement filter (dataset-specific). Examples: 'PC' (percentage), '...
    na_item : str | Any
        National accounts item filter for economic datasets (e.g., 'B1GQ' for GDP, 'P...
    time : str | Any
        Time filter (year or time range). Examples: '2022', '2015:2022' (range)
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
            "name": "Eurostat_get_dataset",
            "arguments": {
                "datasetCode": datasetCode,
                "geo": geo,
                "unit": unit,
                "na_item": na_item,
                "time": time,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Eurostat_get_dataset"]
