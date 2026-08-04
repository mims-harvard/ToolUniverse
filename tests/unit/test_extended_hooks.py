"""Behavioral tests for configurable local output hooks."""

import copy
import json

import pytest

from tooluniverse.agentic_tool import AgenticTool
from tooluniverse.extended_hooks import (
    FilteringHook,
    FormattingHook,
    LoggingHook,
    ValidationHook,
)
from tooluniverse.output_hook import HookManager, OutputHook


class _ToolUniverse:
    all_tool_dict = {}
    callable_functions = {}


def _hook_config(hook_type, **hook_config):
    return {
        "name": hook_type.lower(),
        "type": hook_type,
        "hook_config": hook_config,
    }


def _manager(monkeypatch, config):
    monkeypatch.setattr(AgenticTool, "has_any_api_keys", lambda: False)
    return HookManager(config, _ToolUniverse())


def test_filtering_preserves_nested_structure_and_input():
    hook = FilteringHook(
        _hook_config(
            "FilteringHook",
            filter_patterns=[r"[\w.+-]+@[\w.-]+"],
            replacement_text="[REDACTED]",
        )
    )
    source = {
        "patient": {"contact": "person@example.org", "age": 52},
        "evidence": ["curator@example.org", {"gene": "TP53"}],
        "tuple": ("review@example.org", 7),
    }
    original = copy.deepcopy(source)

    result = hook.process(source, "cancer_tool", {}, {})

    assert result == {
        "patient": {"contact": "[REDACTED]", "age": 52},
        "evidence": ["[REDACTED]", {"gene": "TP53"}],
        "tuple": ("[REDACTED]", 7),
    }
    assert source == original


def test_filtering_can_flatten_output_when_requested():
    hook = FilteringHook(
        _hook_config(
            "FilteringHook",
            filter_patterns=["secret"],
            preserve_structure=False,
        )
    )

    result = hook.process({"value": "secret"}, "tool", {}, {})

    assert isinstance(result, str)
    assert "secret" not in result


def test_filtering_ignores_invalid_patterns_and_keeps_non_strings(capsys):
    hook = FilteringHook(
        _hook_config("FilteringHook", filter_patterns=["(", "private"])
    )

    result = hook.process([4, None, "private"], "tool", {}, {})

    assert result == [4, None, "[REDACTED]"]
    assert "Invalid regex pattern" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ({"b": 2, "a": 1}, '{\n  "a": 1,\n  "b": 2\n}'),
        (["first", "second"], "1. first\n2. second"),
        ("short text", "short text"),
        (42, 42),
    ],
)
def test_formatting_supported_output_types(value, expected):
    hook = FormattingHook(_hook_config("FormattingHook"))
    assert hook.process(value, "tool", {}, {}) == expected


def test_formatting_wraps_long_text_without_losing_words():
    hook = FormattingHook(
        _hook_config("FormattingHook", max_line_length=12)
    )

    result = hook.process("alpha beta gamma delta", "tool", {}, {})

    assert result.splitlines() == ["alpha beta", "gamma delta"]


def test_validation_fix_adds_required_fields_without_mutating_input():
    hook = ValidationHook(
        _hook_config(
            "ValidationHook",
            required_fields=["data", "provenance"],
            error_action="fix",
        )
    )
    source = {"data": [{"gene": "BRCA1"}]}

    result = hook.process(source, "evidence_tool", {}, {})

    assert result == {"data": [{"gene": "BRCA1"}], "provenance": None}
    assert source == {"data": [{"gene": "BRCA1"}]}


@pytest.mark.parametrize("action", ["warn", "fail"])
def test_validation_non_fix_actions_preserve_output(action):
    hook = ValidationHook(
        _hook_config(
            "ValidationHook", required_fields=["missing"], error_action=action
        )
    )
    source = {"data": []}
    assert hook.process(source, "tool", {}, {}) is source


@pytest.mark.parametrize("log_format", ["simple", "detailed", "json"])
def test_logging_formats_write_and_preserve_result(tmp_path, log_format):
    log_path = tmp_path / "nested" / f"{log_format}.log"
    hook = LoggingHook(
        _hook_config(
            "LoggingHook", log_format=log_format, log_file=str(log_path)
        )
    )
    source = {"gene": "EGFR"}

    result = hook.process(
        source,
        "cancer_evidence",
        {"genes": {"TP53", "EGFR"}},
        {"execution_time": 123},
    )

    assert result is source
    content = log_path.read_text(encoding="utf-8")
    assert "cancer_evidence" in content
    if log_format == "json":
        assert json.loads(content)["arguments"]["genes"] in (
            "{'TP53', 'EGFR'}",
            "{'EGFR', 'TP53'}",
        )


def test_logging_truncates_output_preview(tmp_path):
    log_path = tmp_path / "audit.log"
    hook = LoggingHook(
        _hook_config(
            "LoggingHook",
            log_format="json",
            log_file=str(log_path),
            max_log_size=5,
        )
    )
    hook.process("abcdefgh", "tool", {}, {})
    assert json.loads(log_path.read_text(encoding="utf-8"))["output_preview"] == "abcde"


@pytest.mark.parametrize(
    ("hook_type", "hook_class"),
    [
        ("FilteringHook", FilteringHook),
        ("FormattingHook", FormattingHook),
        ("ValidationHook", ValidationHook),
        ("LoggingHook", LoggingHook),
    ],
)
def test_manager_constructs_extended_hook_types(monkeypatch, hook_type, hook_class):
    manager = _manager(monkeypatch, {"hooks": [_hook_config(hook_type)]})
    assert len(manager.hooks) == 1
    assert isinstance(manager.hooks[0], hook_class)
    assert manager.enabled


def test_local_hooks_run_without_llm_credentials(monkeypatch):
    manager = _manager(
        monkeypatch,
        {
            "hooks": [
                _hook_config(
                    "FilteringHook",
                    filter_patterns=["restricted"],
                    replacement_text="approved",
                )
            ]
        },
    )
    result = manager.apply_hooks(
        {"status": "restricted"}, "tool", {}, {"category": "biomedical"}
    )
    assert result == {"status": "approved"}


def test_mixed_config_skips_only_llm_hook_without_credentials(monkeypatch):
    manager = _manager(
        monkeypatch,
        {
            "hooks": [
                _hook_config("SummarizationHook"),
                _hook_config("ValidationHook", required_fields=["data"]),
            ]
        },
    )
    assert [type(hook) for hook in manager.hooks] == [ValidationHook]
    assert manager.enabled


def test_summarization_only_config_retains_disabled_behavior(monkeypatch):
    manager = _manager(
        monkeypatch, {"hooks": [_hook_config("SummarizationHook")]}
    )
    assert not manager.enabled
    assert manager.hooks == []


class _ExplodingHook(OutputHook):
    def process(self, result, tool_name=None, arguments=None, context=None):
        raise RuntimeError("hook failed")


class _AppendHook(OutputHook):
    def process(self, result, tool_name=None, arguments=None, context=None):
        return result + self.config["suffix"]


def test_hook_failures_are_isolated_and_priority_is_stable(caplog):
    manager = object.__new__(HookManager)
    manager.enabled = True
    manager.config = {}
    manager._pending_tools_to_load = []
    manager._excluded_patterns_cache = None
    manager.tooluniverse = _ToolUniverse()
    manager.hooks = [
        _AppendHook({"name": "last", "priority": 30, "suffix": "C"}),
        _ExplodingHook({"name": "broken", "priority": 20}),
        _AppendHook({"name": "first", "priority": 10, "suffix": "B"}),
    ]

    result = manager.apply_hooks("A", "tool", {}, {})

    assert result == "ABC"
    assert "preserving the current result" in caplog.text


def test_tool_and_category_hooks_apply_only_to_matching_calls(monkeypatch):
    config = {
        "tool_specific_hooks": {
            "target_tool": {
                "hooks": [
                    _hook_config(
                        "FilteringHook",
                        filter_patterns=["secret"],
                        replacement_text="tool-match",
                    )
                ]
            }
        },
        "category_hooks": {
            "genomics": {
                "hooks": [
                    _hook_config(
                        "FilteringHook",
                        filter_patterns=["secret"],
                        replacement_text="category-match",
                    )
                ]
            }
        },
    }
    manager = _manager(monkeypatch, config)

    assert (
        manager.apply_hooks("secret", "other", {}, {"category": "other"})
        == "secret"
    )
    assert (
        manager.apply_hooks("secret", "target_tool", {}, {"category": "other"})
        == "tool-match"
    )
    assert (
        manager.apply_hooks("secret", "other", {}, {"category": "genomics"})
        == "category-match"
    )


def test_loading_hooks_does_not_mutate_nested_user_config(monkeypatch):
    config = {
        "tool_specific_hooks": {
            "target": {
                "hooks": [
                    {
                        "type": "FilteringHook",
                        "hook_config": {"filter_patterns": ["private"]},
                    }
                ]
            }
        },
        "hook_type_defaults": {"FilteringHook": {"unused": True}},
    }
    original = copy.deepcopy(config)

    _manager(monkeypatch, config)

    assert config == original


def test_biomedical_pipeline_filters_validates_and_audits_without_llm(
    monkeypatch, tmp_path
):
    log_path = tmp_path / "artifacts" / "cancer-evidence.jsonl"
    config = {
        "hooks": [
            {
                **_hook_config(
                    "FilteringHook",
                    filter_patterns=[r"[\w.+-]+@[\w.-]+"],
                    replacement_text="[REDACTED]",
                ),
                "priority": 10,
            },
            {
                **_hook_config(
                    "ValidationHook",
                    required_fields=["data", "provenance"],
                    error_action="fix",
                ),
                "priority": 20,
            },
            {
                **_hook_config(
                    "LoggingHook",
                    log_format="json",
                    log_file=str(log_path),
                ),
                "priority": 30,
            },
        ]
    }
    manager = _manager(monkeypatch, config)
    source = {
        "data": [
            {"gene": "TP53", "variant": "R175H", "curator": "a@lab.org"},
            {"gene": "EGFR", "variant": "L858R", "curator": "b@lab.org"},
        ]
    }

    result = manager.apply_hooks(
        source,
        "federated_cancer_evidence",
        {"genes": ["TP53", "EGFR"]},
        {"category": "oncology", "execution_time": 123},
    )

    assert result["provenance"] is None
    assert [row["curator"] for row in result["data"]] == [
        "[REDACTED]",
        "[REDACTED]",
    ]
    assert source["data"][0]["curator"] == "a@lab.org"
    audit = json.loads(log_path.read_text(encoding="utf-8"))
    assert audit["tool_name"] == "federated_cancer_evidence"
    assert "[REDACTED]" in audit["output_preview"]
