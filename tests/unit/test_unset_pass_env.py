"""A --pass-env name that is not set hands the model nothing, and used to say nothing.

The flag exists for variables that are unusual -- a site licence server, an internal CA -- so a
typo in one is cheap to make and expensive to find: the pool starts, the model runs, and it
fails later for a reason that no longer looks like a mistake in a flag.

Measured before this: `--pass-env TYPO_VARIABLE` put the name in the allow-list and nothing in
the child environment, with no output at all.
"""

from __future__ import annotations

import pytest

from tooluniverse.cli import unset_pass_env_warning


def test_nothing_is_said_when_every_name_is_set():
    assert unset_pass_env_warning(["A", "B"], {"A": "1", "B": "2"}) == ""


def test_nothing_is_said_when_the_flag_was_not_used():
    assert unset_pass_env_warning([], {}) == ""


def test_an_unset_name_is_named_with_what_to_do():
    message = unset_pass_env_warning(["SITE_LICENCE"], {})

    assert "SITE_LICENCE" in message
    assert "not set in this shell" in message
    # A warning without a next move is just noise.
    assert "Export it first" in message


def test_only_the_unset_names_are_listed():
    """Naming a variable the person did set would send them looking in the wrong place."""
    message = unset_pass_env_warning(["SET_ONE", "MISSING"], {"SET_ONE": "value"})

    assert "MISSING" in message
    assert "SET_ONE" not in message


def test_an_empty_value_counts_as_unset():
    """Exporting a variable to the empty string hands the model nothing it can use."""
    for value in ("", "   ", "\t\n"):
        message = unset_pass_env_warning(["BLANK"], {"BLANK": value})

        assert "BLANK" in message, repr(value)


def test_a_value_of_zero_or_false_is_still_a_value():
    """Strings a person might reasonably pass that must not be read as missing."""
    for value in ("0", "false", "no", "None"):
        assert unset_pass_env_warning(["FLAGGY"], {"FLAGGY": value}) == "", value


@pytest.mark.parametrize(
    "names, expected_words",
    [
        (["ONE"], ("is not set", "it will not", "Export it")),
        (["ONE", "TWO"], ("are not set", "they will not", "Export them")),
    ],
)
def test_the_sentence_agrees_with_how_many_are_missing(names, expected_words):
    message = unset_pass_env_warning(names, {})

    for word in expected_words:
        assert word in message, message


def test_every_missing_name_appears_once():
    message = unset_pass_env_warning(["A", "B", "C"], {})

    for name in ("A", "B", "C"):
        assert message.count(name) >= 1
    assert message.count("--pass-env") == 1


def test_the_warning_never_prints_a_value():
    """The whole point of these variables is that they may be credentials."""
    message = unset_pass_env_warning(["TOKEN", "MISSING"], {"TOKEN": "sk-SECRET-VALUE"})

    assert "SECRET" not in message
    assert "sk-" not in message
