"""Regression guard for Feature-26A-8: the framework injected an `operation`
parameter and then blamed the caller for it.

`ToolUniverse._apply_operation_default` fills `operation` into `arguments` from
the tool's own config before validation, because many single-operation
registrations still read `arguments["operation"]`. Validation treated that
injected key as caller-supplied, so
`Pharos_get_target_expression {"target": "EGFR"}` was answered with
"Unrecognized parameter(s): 'target', 'operation'" -- naming a parameter the
caller never sent and cannot remove.

The auto-supplied value is now recognized (it is exactly what the config would
have supplied) and left out of both the message and
`details["unknown_parameters"]`, while a caller-supplied `operation` saying
anything else is still reported. Leaving it out of the argument set the
unknown-key check sees also keeps the Feature-14A-01 total-mismatch guard
honest: the injected key must pad neither the "recognized" side (for the 348
configs that declare `operation`) nor the "unknown" side (for the 235 that do
not).
"""

import json
from pathlib import Path

import pytest

from tooluniverse.base_tool import BaseTool, resolve_configured_operation

pytestmark = pytest.mark.unit

_DATA_DIR = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data"

# A tool class that reads its operation from the config, so the schema never
# declares `operation` -- the shape that produced the reported message.
_PHAROS_TOOL = "Pharos_get_target_expression"

# The other shape in the corpus: `operation` declared as a schema property.
_DECLARED_OPERATION_CONFIG = {
    "name": "Fake_declared_operation_tool",
    "parameter": {
        "type": "object",
        "properties": {
            "operation": {"type": "string"},
            "query": {"type": "string"},
        },
        "required": [],
    },
    "fields": {"operation": "search"},
}


def _config(name, filename):
    configs = json.loads((_DATA_DIR / filename).read_text())
    for cfg in configs:
        if cfg["name"] == name:
            return cfg
    raise AssertionError(f"{name} not found in {filename}")


def _pharos_tool():
    return BaseTool(_config(_PHAROS_TOOL, "pharos_tools.json"))


class TestConfiguredOperationResolution:
    def test_reads_fields_operation(self):
        assert (
            resolve_configured_operation(_config(_PHAROS_TOOL, "pharos_tools.json"))
            == "get_target_expression"
        )

    def test_falls_back_to_schema_default(self):
        cfg = {
            "parameter": {"properties": {"operation": {"default": "search"}}},
        }
        assert resolve_configured_operation(cfg) == "search"

    def test_returns_none_when_no_operation_is_configured(self):
        assert resolve_configured_operation({"parameter": {"properties": {}}}) is None


class TestAutoSuppliedOperationIsNotBlamed:
    """The injected key must never look caller-supplied."""

    def test_message_names_only_the_caller_supplied_key(self):
        error = _pharos_tool().validate_parameters(
            {"target": "EGFR", "operation": "get_target_expression"}
        )

        assert error is not None
        assert "'target'" in str(error)
        assert "operation" not in str(error)
        # The corrective half of the message must survive.
        assert "This tool accepts: gene, uniprot." in str(error)

    def test_details_do_not_list_the_injected_key(self):
        error = _pharos_tool().validate_parameters(
            {"target": "EGFR", "operation": "get_target_expression"}
        )

        assert error.details["unknown_parameters"] == ["target"]

    def test_valid_call_with_injected_operation_still_validates(self):
        assert (
            _pharos_tool().validate_parameters(
                {"gene": "EGFR", "operation": "get_target_expression"}
            )
            is None
        )

    def test_injected_operation_alone_is_not_reported(self):
        assert (
            _pharos_tool().validate_parameters({"operation": "get_target_expression"})
            is None
        )


class TestCallerSuppliedOperationIsStillReported:
    """A genuinely wrong `operation` from the caller must still be named."""

    def test_bogus_operation_is_rejected(self):
        error = _pharos_tool().validate_parameters({"operation": "totally_bogus"})

        assert error is not None
        assert "'operation'" in str(error)
        assert error.details["unknown_parameters"] == ["operation"]

    def test_bogus_operation_is_reported_even_though_a_default_exists(self):
        # The tool has fields.operation set; only the *matching* value is
        # treated as auto-supplied.
        error = _pharos_tool().validate_parameters(
            {"operation": "get_target_expression_v2"}
        )

        assert error is not None
        assert "'operation'" in str(error)


class TestTotalMismatchGuardNotWeakened:
    """Feature-14A-01: a fully unrecognized parameter set must be rejected."""

    def test_guard_fires_when_operation_is_declared_in_the_schema(self):
        tool = BaseTool(_DECLARED_OPERATION_CONFIG)

        error = tool.validate_parameters(
            {"zzz_bogus": "x", "operation": "search"}  # operation auto-supplied
        )

        assert error is not None
        assert "'zzz_bogus'" in str(error)
        assert error.details["unknown_parameters"] == ["zzz_bogus"]

    def test_guard_fires_when_operation_is_not_declared(self):
        error = _pharos_tool().validate_parameters(
            {"target": "EGFR", "operation": "get_target_expression"}
        )

        assert error is not None

    def test_recognized_parameter_mixed_with_the_injected_key_is_accepted(self):
        tool = BaseTool(_DECLARED_OPERATION_CONFIG)

        assert (
            tool.validate_parameters({"query": "kinase", "operation": "search"}) is None
        )


class TestInjectionItselfIsUnchanged:
    """Only the reporting changes -- tool classes that read
    arguments["operation"] must keep receiving it."""

    def test_operation_is_still_injected_before_the_tool_runs(self):
        from tooluniverse import ToolUniverse

        engine = ToolUniverse()
        engine.load_tools(tool_type=["pharos"])

        args = {"gene": "EGFR"}
        engine._apply_operation_default(_PHAROS_TOOL, args)

        assert args["operation"] == "get_target_expression"

    def test_end_to_end_message_does_not_name_the_injected_key(self):
        from tooluniverse import ToolUniverse

        engine = ToolUniverse()
        engine.load_tools(tool_type=["pharos"])

        result = engine.run({"name": _PHAROS_TOOL, "arguments": {"target": "EGFR"}})

        assert result["status"] == "error"
        assert "operation" not in result["error"]
        assert result["error_details"]["details"]["unknown_parameters"] == ["target"]
