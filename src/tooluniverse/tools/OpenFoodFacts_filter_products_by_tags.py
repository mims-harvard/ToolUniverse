"""
OpenFoodFacts_filter_products_by_tags

Structured / faceted product search of the Open Food Facts database via the v2 search API. Filter...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenFoodFacts_filter_products_by_tags(
    additives_tags: Optional[str] = None,
    allergens_tags: Optional[str] = None,
    categories_tags_en: Optional[str] = None,
    brands_tags: Optional[str] = None,
    nutrition_grades_tags: Optional[str] = None,
    labels_tags: Optional[str] = None,
    countries_tags: Optional[str] = None,
    fields: Optional[str] = None,
    page_size: Optional[int] = None,
    page: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Structured / faceted product search of the Open Food Facts database via the v2 search API. Filter...

    Parameters
    ----------
    additives_tags : str
        Filter by food-additive tag, e.g. 'en:e322' (lecithin), 'en:e330' (citric aci...
    allergens_tags : str
        Filter by allergen tag, e.g. 'en:peanuts', 'en:milk', 'en:gluten'.
    categories_tags_en : str
        Filter by English category name, e.g. 'Sodas', 'Breakfast cereals', 'Olive oi...
    brands_tags : str
        Filter by brand tag, e.g. 'coca-cola', 'nestle'.
    nutrition_grades_tags : str
        Filter by Nutri-Score grade: 'a', 'b', 'c', 'd', or 'e'.
    labels_tags : str
        Filter by label tag, e.g. 'en:organic', 'en:vegan', 'en:gluten-free', 'en:fai...
    countries_tags : str
        Filter by country tag, e.g. 'en:france', 'en:united-states'.
    fields : str
        Comma-separated list of product fields to return. Default: product_name,code,...
    page_size : int
        Number of results per page (1-100). Default: 20
    page : int
        Page number for pagination. Default: 1
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
            "additives_tags": additives_tags,
            "allergens_tags": allergens_tags,
            "categories_tags_en": categories_tags_en,
            "brands_tags": brands_tags,
            "nutrition_grades_tags": nutrition_grades_tags,
            "labels_tags": labels_tags,
            "countries_tags": countries_tags,
            "fields": fields,
            "page_size": page_size,
            "page": page,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OpenFoodFacts_filter_products_by_tags",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenFoodFacts_filter_products_by_tags"]
