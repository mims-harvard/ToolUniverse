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
50 is what was kept. Rather than only describing Open Food Facts' unversioned
server default, the schema now declares ``default: 50``, which
``BaseRESTTool._build_params`` injects into the request -- so the number is
owned by this repo and stays true even if Open Food Facts changes theirs.
Verified live that the response is unchanged either way (``page_size 50``,
``count 2577`` for "almond milk"), and that an explicit ``page_size: 10`` is
still honoured.
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


def test_search_products_declares_the_default_it_documents():
    """The number must be enforced by the schema, not just asserted in prose.

    Declaring it means BaseRESTTool sends page_size=50 explicitly, so the
    description cannot be silently falsified by an upstream default change.
    """
    page_size = _page_size("OpenFoodFacts_search_products")
    assert page_size["default"] == 50
    assert "50" in page_size["description"]
    assert "Default: 10" not in page_size["description"]


def test_filter_by_tags_default_is_left_alone():
    """This sibling's documented 20 is correct -- verified live. Do not touch."""
    description = _page_size("OpenFoodFacts_filter_products_by_tags")["description"]
    assert "20" in description
