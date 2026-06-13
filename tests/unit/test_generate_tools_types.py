"""Unit tests for the coding-API stub generator's type-annotation logic.

Guards a regression where a nullable JSON type such as ``["string", "null"]``
was annotated as ``Optional[str | Any]`` instead of ``Optional[str]``: the
``"null"`` member must be dropped, since a field's optionality is expressed by
the surrounding ``Optional[...]`` wrapper, not by a ``| Any`` union.
"""

import pytest

from tooluniverse.generate_tools import (
    json_type_to_python,
    prop_to_python_type,
    sanitize_param_name,
)


@pytest.mark.unit
class TestPropToPythonType:
    def test_nullable_string_drops_null(self):
        """["string", "null"] is a nullable string -> str (not "str | Any")."""
        assert prop_to_python_type({"type": ["string", "null"]}) == "str"

    def test_nullable_integer_drops_null(self):
        """["integer", "null"] -> int, with the null member dropped."""
        assert prop_to_python_type({"type": ["integer", "null"]}) == "int"

    def test_single_element_list_unchanged(self):
        """A single-element type list resolves to that one type."""
        assert prop_to_python_type({"type": ["string"]}) == "str"

    def test_plain_string_type(self):
        """A plain (non-list) string type maps to str."""
        assert prop_to_python_type({"type": "string"}) == "str"

    def test_legitimate_union_preserved(self):
        """A real multi-type union must still be reported (null is the only drop)."""
        assert prop_to_python_type({"type": ["string", "array"]}) == "str | list[Any]"

    def test_oneof_with_null_drops_null(self):
        """oneOf containing a null branch collapses to the non-null type."""
        prop = {"oneOf": [{"type": "string"}, {"type": "null"}]}
        assert prop_to_python_type(prop) == "str"

    def test_oneof_union_preserved(self):
        """oneOf with two real types keeps the union annotation."""
        prop = {"oneOf": [{"type": "string"}, {"type": "array"}]}
        assert prop_to_python_type(prop) == "str | list[Any]"

    def test_array_of_strings(self):
        """An array with string items annotates as list[str]."""
        prop = {"type": "array", "items": {"type": "string"}}
        assert prop_to_python_type(prop) == "list[str]"

    def test_only_null_falls_back_to_any(self):
        """A degenerate null-only schema falls back to Any (no crash, no '| Any')."""
        assert prop_to_python_type({"type": ["null"]}) == "Any"


@pytest.mark.unit
class TestSanitizeParamName:
    """A tool param must never collide with the generator's injected kw-only args."""

    @pytest.mark.parametrize("reserved", ["use_cache", "validate", "stream_callback"])
    def test_injected_name_collision_suffixed(self, reserved):
        """A param named like an injected arg gets a trailing underscore."""
        assert sanitize_param_name(reserved) == reserved + "_"

    def test_python_keyword_suffixed(self):
        """A Python keyword param is suffixed (pre-existing behavior preserved)."""
        assert sanitize_param_name("for") == "for_"

    def test_ordinary_name_unchanged(self):
        """An ordinary param name passes through untouched."""
        assert sanitize_param_name("query") == "query"

    def test_dots_and_hyphens_normalized(self):
        """Dots and hyphens become underscores."""
        assert sanitize_param_name("query.cond") == "query_cond"
        assert sanitize_param_name("from-date") == "from_date"


@pytest.mark.unit
class TestJsonTypeToPython:
    """The simpler helper already filtered null; pin that behavior too."""

    def test_nullable_string(self):
        """A nullable string list yields Optional[str] from the simple helper."""
        assert json_type_to_python(["string", "null"]) == "Optional[str]"

    def test_plain_integer(self):
        """A plain integer type maps to int."""
        assert json_type_to_python("integer") == "int"

    def test_unknown_type_is_any(self):
        """An unrecognized type name falls back to Any."""
        assert json_type_to_python("widget") == "Any"
