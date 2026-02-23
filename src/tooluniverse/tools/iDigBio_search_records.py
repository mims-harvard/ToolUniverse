"""
iDigBio_search_records

Search iDigBio (Integrated Digitized Biocollections) for natural history specimen records from 80...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def iDigBio_search_records(
    scientificname: Optional[str | Any] = None,
    kingdom: Optional[str | Any] = None,
    phylum: Optional[str | Any] = None,
    family: Optional[str | Any] = None,
    genus: Optional[str | Any] = None,
    country: Optional[str | Any] = None,
    stateprovince: Optional[str | Any] = None,
    institutioncode: Optional[str | Any] = None,
    limit: Optional[int | Any] = None,
    offset: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search iDigBio (Integrated Digitized Biocollections) for natural history specimen records from 80...

    Parameters
    ----------
    scientificname : str | Any
        Scientific name to search for. Examples: 'Quercus robur', 'Homo sapiens', 'Dr...
    kingdom : str | Any
        Kingdom filter. Values: 'Plantae', 'Animalia', 'Fungi', 'Bacteria', 'Chromista'
    phylum : str | Any
        Phylum filter. Examples: 'Chordata', 'Arthropoda', 'Magnoliophyta'
    family : str | Any
        Family filter. Examples: 'Rosaceae', 'Felidae', 'Orchidaceae'
    genus : str | Any
        Genus filter. Examples: 'Rosa', 'Quercus', 'Drosophila'
    country : str | Any
        Country filter. Examples: 'United States', 'Germany', 'Brazil'
    stateprovince : str | Any
        State or province filter. Examples: 'California', 'Bavaria', 'Minas Gerais'
    institutioncode : str | Any
        Institution code filter. Examples: 'USNM' (Smithsonian), 'CAS' (California Ac...
    limit : int | Any
        Maximum number of records to return (default 10, max 5000)
    offset : int | Any
        Offset for pagination
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
            "name": "iDigBio_search_records",
            "arguments": {
                "scientificname": scientificname,
                "kingdom": kingdom,
                "phylum": phylum,
                "family": family,
                "genus": genus,
                "country": country,
                "stateprovince": stateprovince,
                "institutioncode": institutioncode,
                "limit": limit,
                "offset": offset,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["iDigBio_search_records"]
