#!/usr/bin/env python3
"""
Parameter Validation Demo

Demonstrates real parameter validation errors with actual tool schemas.

A tool call RETURNS its error; it does not raise. `tooluniverse.exceptions`
defines ToolValidationError and friends, but the call path converts them with
`_create_dual_format_error` and hands back
`{"status": "error", "error": ..., "error_details": {...}}`. This file used to
wrap every case in `try`/`except ToolValidationError` and read `e.message`,
`e.field` and `e.value` -- the except never fired, and none of those three
attributes exists on the class. Each case below prints what the call really
returns; every message quoted in a comment was produced by running it.
"""

from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()


def report(label, result):
    """Print a result the way the error contract actually works."""
    if isinstance(result, dict) and result.get("status") == "error":
        # .get(): a tool reporting an upstream failure of its own may send no
        # error_details at all, so do not index into it.
        details = result.get("error_details") or {}
        print(f"{label}: error")
        print(f"  message   : {result['error']}")
        print(f"  kind      : {details.get('type')}")  # the exception class name
        print(f"  retriable : {details.get('retriable')}")
        print(f"  next steps: {details.get('next_steps')}")
    else:
        print(f"{label}: ok ({type(result).__name__})")


# =============================================================================
# Method 1: Missing Required Parameter
# =============================================================================
# Syntax: tu.tools.ToolName() - missing required parameter
# -> error_details["type"] == "ToolValidationError"
#    "Parameter validation failed for 'root': 'accession' is a required property"
report("missing required", tu.tools.UniProt_get_entry_by_accession())

# =============================================================================
# Method 2: Wrong Parameter Type
# =============================================================================
# Syntax: tu.tools.ToolName(param="string") when param expects integer
# -> "Parameter validation failed for 'max_results': 'ten' is not of type 'integer'"
report(
    "wrong type",
    tu.tools.openalex_literature_search(
        search_keywords="AI",
        max_results="ten",  # schema says integer
    ),
)

# =============================================================================
# Method 3: Value Out of Range
# =============================================================================
# Syntax: tu.tools.ToolName(param=value) when value exceeds maximum
# -> "Parameter validation failed for 'max_results': 500 is greater than the
#     maximum of 200"
report(
    "out of range",
    tu.tools.openalex_literature_search(
        search_keywords="AI",
        max_results=500,  # schema maximum is 200
    ),
)

# =============================================================================
# Method 4: Valid Parameters
# =============================================================================
report("valid", tu.tools.UniProt_get_entry_by_accession(accession="P05067"))

# =============================================================================
# Method 5: Not Every Error Is a Validation Error
# =============================================================================
# An empty accession satisfies the schema -- it is a string -- so validation
# passes, the call goes out, and UniProt answers 404. The result is still an
# error dict, but one with NO error_details:
#   {"status": "error", "error": "UniProt API returned status code: 404"}
# This is why `kind` prints None here and why error_details must be read with
# .get() rather than indexed.
report("empty accession", tu.tools.UniProt_get_entry_by_accession(accession=""))

# =============================================================================
# Method 6: Skipping Validation
# =============================================================================
# validate=True is the default. Turning it off sends the arguments as given, so
# a schema violation becomes whatever the upstream API makes of it instead of a
# ToolValidationError.
report(
    "validate=False",
    tu.tools.openalex_literature_search(
        search_keywords="AI",
        max_results=500,
        validate=False,
    ),
)

# =============================================================================
# The one exception you do get
# =============================================================================
# It does not come from a call. `tu.tools` raises AttributeError for a tool name
# that does not exist.
try:
    tu.tools.NameThatDoesNotExist(param="x")
except AttributeError as e:
    print(f"unknown tool name: AttributeError - {e}")

# =============================================================================
# Summary
# =============================================================================
# Validation catches missing required parameters, wrong types, and values
# outside the declared range, and reports each as an error dict whose
# error_details["type"] is "ToolValidationError", with next_steps and retriable
# alongside. Everything else that can go wrong -- an upstream 404, a timeout, a
# missing credential -- also arrives as an error dict, so branch on
# result["status"], never on an exception.
