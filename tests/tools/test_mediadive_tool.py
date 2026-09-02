"""Tests for the MediaDive cultivation media tool.

MediaDive (DSMZ) pairs with the already-wrapped BacDive: BacDive says what
an organism is, this says what to grow it in. Tests assert a real, known
recipe survives the round trip rather than checking response shape alone.
"""

import pytest
from tooluniverse import ToolUniverse


TRANSIENT = ("timed out", "Failed to connect", "HTTP 5")

NUTRIENT_AGAR = 1
AGAR_INGREDIENT = 3


@pytest.fixture(scope="module")
def tu():
    instance = ToolUniverse()
    instance.load_tools()
    return instance


def data_of(result):
    if result.get("status") == "error":
        error = str(result.get("error", ""))
        if any(t in error for t in TRANSIENT):
            pytest.skip(f"upstream temporarily unavailable: {error[:80]}")
        pytest.fail(f"unexpected error response: {error[:200]}")
    return result["data"]


class TestRegistration:
    def test_tools_load(self, tu):
        names = {t.get("name") for t in tu.all_tools if isinstance(t, dict)}
        assert "MediaDive_search_media" in names
        assert "MediaDive_get_medium" in names
        assert "MediaDive_search_ingredients" in names
        assert "MediaDive_get_ingredient" in names


class TestSearchMedia:
    def test_finds_nutrient_agar(self, tu):
        rows = data_of(tu.tools.MediaDive_search_media(query="nutrient agar"))
        assert any(r["medium_id"] == NUTRIENT_AGAR for r in rows)

    def test_limit_is_respected(self, tu):
        rows = data_of(tu.tools.MediaDive_search_media(query="agar", limit=3))
        assert len(rows) <= 3

    def test_unmatched_query(self, tu):
        result = tu.tools.MediaDive_search_media(query="zzzznotamedium12345")
        assert result["status"] == "error"

    def test_missing_query(self, tu):
        assert tu.tools.MediaDive_search_media(query="")["status"] == "error"


class TestGetMedium:
    def test_nutrient_agar_recipe_has_known_ingredients(self, tu):
        data = data_of(tu.tools.MediaDive_get_medium(medium_id=NUTRIENT_AGAR))
        assert data["name"] == "NUTRIENT AGAR"
        compounds = {
            ing["compound"]
            for solution in data["solutions"]
            for ing in solution["recipe"]
        }
        assert "Peptone" in compounds
        assert "Agar" in compounds

    def test_amounts_are_reported_in_grams_per_liter(self, tu):
        data = data_of(tu.tools.MediaDive_get_medium(medium_id=NUTRIENT_AGAR))
        recipe = data["solutions"][0]["recipe"]
        agar = next(r for r in recipe if r["compound"] == "Agar")
        assert agar["grams_per_liter"] == 15

    def test_preparation_steps_are_included(self, tu):
        data = data_of(tu.tools.MediaDive_get_medium(medium_id=NUTRIENT_AGAR))
        assert any(data["solutions"][0]["preparation_steps"])

    def test_string_identifier_medium(self, tu):
        # MediaDive uses alphanumeric ids like '1a' alongside plain integers.
        result = tu.tools.MediaDive_get_medium(medium_id="1a")
        assert result["status"] == "success"

    def test_unknown_medium(self, tu):
        result = tu.tools.MediaDive_get_medium(medium_id=999999999)
        assert result["status"] == "error"

    def test_missing_medium_id(self, tu):
        assert tu.tools.MediaDive_get_medium(medium_id="")["status"] == "error"


class TestSearchIngredients:
    def test_finds_agar(self, tu):
        rows = data_of(tu.tools.MediaDive_search_ingredients(query="agar"))
        assert any(r["ingredient_id"] == AGAR_INGREDIENT for r in rows)

    def test_limit_is_respected(self, tu):
        rows = data_of(
            tu.tools.MediaDive_search_ingredients(query="extract", limit=2)
        )
        assert len(rows) <= 2

    def test_unmatched_query(self, tu):
        result = tu.tools.MediaDive_search_ingredients(query="zzzznotacompound12345")
        assert result["status"] == "error"


class TestGetIngredient:
    def test_agar_has_known_chemical_identity(self, tu):
        data = data_of(tu.tools.MediaDive_get_ingredient(ingredient_id=AGAR_INGREDIENT))
        assert data["name"] == "Agar"
        assert data["cas_number"] == "9002-18-0"
        assert data["formula"] == "(C12H18O9)n"

    def test_media_usage_is_summarized_not_dumped(self, tu):
        # Peptone appears in hundreds of media; the sample must stay capped.
        data = data_of(tu.tools.MediaDive_get_ingredient(ingredient_id=1))
        assert data["used_in_media_count"] > 20
        assert len(data["used_in_media_sample"]) <= 20

    def test_unknown_ingredient(self, tu):
        result = tu.tools.MediaDive_get_ingredient(ingredient_id=999999999)
        assert result["status"] == "error"

    def test_missing_ingredient_id(self, tu):
        assert tu.tools.MediaDive_get_ingredient(ingredient_id="")["status"] == "error"


class TestErrorHandling:
    @pytest.mark.parametrize(
        "tool_name,kwargs",
        [
            ("MediaDive_search_media", {"query": ""}),
            ("MediaDive_get_medium", {"medium_id": 999999999}),
            ("MediaDive_search_ingredients", {"query": ""}),
            ("MediaDive_get_ingredient", {"ingredient_id": 999999999}),
        ],
    )
    def test_returns_error_dict_not_exception(self, tu, tool_name, kwargs):
        result = getattr(tu.tools, tool_name)(**kwargs)
        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert isinstance(result.get("error"), str) and result["error"]
