"""Turn Python values into R literals for the Rscript-backed tools.

The R tools (``DESeq2Tool``, ``EdgeRLimmaTool``) build a script as text and hand
it to ``Rscript -e``. A value pasted straight into that text is *code*, not data:
a file path or a design formula carrying a quote closes the literal it was meant
to sit inside, and whatever follows runs as R. Tool arguments come from a model
or an upstream request, so the value is not ours to trust.

Every value therefore goes through one of the helpers here, each of which either
returns a literal that cannot escape its own syntax or raises ``ValueError``
naming the argument. The helpers return the literal *including* its quotes, so a
template never writes quotes of its own -- a template that did would reintroduce
the bug the moment someone passed an already quoted value.
"""

import json
import math
import re
from typing import Any

__all__ = ["r_string", "r_number", "r_formula", "r_identifier", "r_level"]

# R accepts the escapes JSON produces (\" \\ \n \t \uXXXX), so a JSON string is
# a valid R string. Unicode is escaped rather than passed through, which also
# keeps the script ASCII whatever the caller's locale.
_IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9._]*$")

# A formula ends up inside `as.formula(...)`, so quoting is what makes it safe
# and this check is only about shape: a tilde, then names, the operators R's
# formula syntax uses, and grouping. A backtick-quoted segment is allowed
# because R needs it for a column whose name has a space in it, and its
# contents are free -- they are part of the quoted string either way.
_FORMULA = re.compile(r"^~(?:[A-Za-z0-9._+*:/\s()-]|`[^`]*`)*$")


def r_string(value: Any) -> str:
    """Return ``value`` as an R string literal, quotes included."""
    return json.dumps("" if value is None else str(value))


def r_number(value: Any, name: str) -> str:
    """Return ``value`` as an R numeric literal.

    Accepts anything ``float()`` accepts, including a numeric string, and
    rejects everything else -- a number interpolated without this check is a
    second way to inject code, since it is written without quotes.
    """
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a number, got {value!r}") from None
    if math.isnan(number) or math.isinf(number):
        raise ValueError(f"{name} must be a finite number, got {value!r}")
    return repr(number)


def r_identifier(value: Any, name: str) -> str:
    """Return ``value`` unquoted, for the few places R needs a bare name.

    Used for a package name in ``library(...)``. Anything that is not a plain R
    name is refused, because here the value really is code.
    """
    text = "" if value is None else str(value)
    if not _IDENTIFIER.match(text):
        raise ValueError(
            f"{name} must be an R name (letters, digits, '.' and '_'), got {text!r}"
        )
    return text


def r_formula(value: Any, name: str) -> str:
    """Return a design formula as an R string literal for ``as.formula``.

    The formula is quoted like any other string, so the check is not what stops
    an injection -- it is what turns a malformed design into an error naming the
    argument instead of an R parse failure three hundred lines into a script.
    """
    text = ("" if value is None else str(value)).strip()
    if not _FORMULA.match(text):
        raise ValueError(
            f"{name} must be a formula such as '~ condition' or "
            f"'~ batch + condition', got {text!r}"
        )
    return r_string(text)


def r_level(value: Any, name: str) -> str:
    """Return one comma-separated factor or level name as an R string literal.

    The callers split these out of a comma-separated argument, so a value
    containing a comma means the argument was not the shape it claimed to be.
    """
    text = ("" if value is None else str(value)).strip()
    if not text or "," in text:
        raise ValueError(f"{name} must not be empty or contain a comma, got {text!r}")
    return r_string(text)
