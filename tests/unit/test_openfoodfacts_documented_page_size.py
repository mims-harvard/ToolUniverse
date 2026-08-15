"""Regression guard: OpenFoodFacts_search_products' documented default was wrong.

``page_size`` was described as "Default: 10". No default was ever applied --
the schema declares none, so ``BaseRESTTool._build_params`` has nothing to
inject and Open Food Facts' own default for ``/cgi/search.pl`` (50) is what
callers actually get. Confirmed live::

    tu run OpenFoodFacts_search_products '{"search_terms": "almond milk"}'
      -> page_size 50, 50 products   (documented: 10)

The sibling ``OpenFoodFacts_filter_products_by_tags`` runs against a different
endpoint and genuinely returns 20, matching its own documented default --
confirmed live the same way -- so only the one description was wrong and this
must not be "fixed" across both.

Returning 50 is the better behaviour (a caller wanting 10 passes 10), so the
description is what was corrected, not the behaviour. This test pins the two
descriptions against each other so the wrong number cannot come back.
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

CONFIG_PATH = (
    Path(__file__).parent.parent.parent
    / "src/tooluniverse/data/openfoodfacts_tools.json"
)
CONFIGS = {c["name"]: c for c in json.loads(CONFIG_PATH.read_text())}


def _page_size(name):
    return CONFIGS[name]["parameter"]["properties"]["page_size"]


def test_search_products_documents_the_default_it_actually_gets():
    description = _page_size("OpenFoodFacts_search_products")["description"]
    assert "50" in description
    assert "Default: 10" not in description


def test_search_products_declares_no_schema_default():
    """The description promises upstream's default; a schema default would
    override it and silently make the description wrong again."""
    assert "default" not in _page_size("OpenFoodFacts_search_products")


def test_filter_by_tags_default_is_left_alone():
    """This sibling's documented 20 is correct -- verified live. Do not touch."""
    description = _page_size("OpenFoodFacts_filter_products_by_tags")["description"]
    assert "20" in description
