"""A tool can need a program pip cannot install, and the sweep had no word for it.

`required_packages` names Python distributions and `requires_local_input` names
the caller's data. Neither describes mmseqs or foldseek: they are C++ binaries,
not on PyPI, resolved from PATH or from TOOLUNIVERSE_MMSEQS2_BINARY /
TOOLUNIVERSE_FOLDSEEK_BINARY. So the sweep ran protein_similarity_local on a
host with neither installed and recorded

    ❌ ProteinSimilarity_search_sequence_local Ex 1: Failed - Install the
       mmseqs CPU binary on this host, or set TOOLUNIVERSE_MMSEQS2_BINARY ...

as two test failures -- a category reported broken with nothing about the tool
to fix. `required_binaries` declares them, and the runner skips with the reason.

Checked before declaring anything, the way #839 checked required_packages:
exactly two tools in the tree declare required_binaries, both in
protein_similarity_local, which was failing 0/2 on this host, in CI (whose apt
list installs neither) and in the weekly sweep. So this relabels failures and
hides no working tool -- and with TOOLUNIVERSE_MMSEQS2_BINARY pointing at a
real executable the sequence tool runs instead of being skipped, which is the
property that keeps it from hiding one later.

The same pass names the skips that had no name. `_format_result_status`
attributed every unnamed skip to a missing credential, so `geant4`, whose one
tool ships no test examples at all, was reported as "1 tool(s) need a
credential this run does not have".
"""

import importlib.util
import json
import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "src" / "tooluniverse" / "data"


def _module(path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _runner(name):
    return _module("scripts/test_new_tools.py", name)


def test_a_program_on_path_is_not_reported_missing():
    assert _runner("tnt_bin1")._missing_binaries(["bash"]) == []


def test_a_missing_program_is_reported_with_its_env_var():
    missing = _runner("tnt_bin2")._missing_binaries(
        [{"name": "tu-probe-no-such-binary", "env_var": "TU_PROBE_BINARY"}]
    )

    assert missing == ["tu-probe-no-such-binary (or $TU_PROBE_BINARY)"]


def test_a_bare_name_needs_no_env_var():
    missing = _runner("tnt_bin3")._missing_binaries(["tu-probe-no-such-binary"])

    assert missing == ["tu-probe-no-such-binary"]


def test_an_env_var_pointing_at_an_executable_satisfies_the_requirement():
    """This is what stops the skip from hiding a host that has the program."""
    runner = _runner("tnt_bin4")
    entry = [{"name": "tu-probe-no-such-binary", "env_var": "TU_PROBE_BINARY"}]

    os.environ["TU_PROBE_BINARY"] = "/usr/bin/env"
    try:
        assert runner._missing_binaries(entry) == []
    finally:
        del os.environ["TU_PROBE_BINARY"]


@pytest.mark.parametrize("target", ["/usr/bin/tu-probe-absent", "/etc/hostname"])
def test_an_env_var_pointing_at_a_non_executable_does_not(target):
    """A path that is missing, or present but not executable, is still missing."""
    runner = _runner("tnt_bin5")
    entry = [{"name": "tu-probe-no-such-binary", "env_var": "TU_PROBE_BINARY"}]

    os.environ["TU_PROBE_BINARY"] = target
    try:
        assert runner._missing_binaries(entry) == [
            "tu-probe-no-such-binary (or $TU_PROBE_BINARY)"
        ]
    finally:
        del os.environ["TU_PROBE_BINARY"]


def test_an_empty_or_malformed_declaration_skips_nothing():
    runner = _runner("tnt_bin6")

    assert runner._missing_binaries([]) == []
    assert runner._missing_binaries([None, 42, {}, {"env_var": "X"}]) == []


def test_the_runner_skips_before_trying_the_tool():
    source = (ROOT / "scripts" / "test_new_tools.py").read_text("utf-8")

    assert 'tool.get("required_binaries")' in source
    assert "skipped_missing_binary" in source
    assert "Skipped missing binary:" in source


def test_the_two_local_similarity_tools_declare_their_binaries():
    tools = json.loads(
        (DATA / "protein_similarity_local_tools.json").read_text("utf-8")
    )
    declared = {
        t["name"]: t.get("required_binaries") for t in tools
    }

    assert declared["ProteinSimilarity_search_sequence_local"] == [
        {"name": "mmseqs", "env_var": "TOOLUNIVERSE_MMSEQS2_BINARY"}
    ]
    assert declared["ProteinSimilarity_search_structure_local"] == [
        {"name": "foldseek", "env_var": "TOOLUNIVERSE_FOLDSEEK_BINARY"}
    ]


def test_only_those_two_tools_declare_a_binary():
    """The check that this relabels failures instead of hiding working tools."""
    declaring = []
    for path in DATA.glob("**/*.json"):
        if "broken_apis" in path.parts:
            continue
        try:
            content = json.loads(path.read_text("utf-8"))
        except ValueError:
            continue
        if not isinstance(content, list):
            continue
        for tool in content:
            if isinstance(tool, dict) and tool.get("required_binaries"):
                declaring.append(tool["name"])

    assert sorted(declaring) == [
        "ProteinSimilarity_search_sequence_local",
        "ProteinSimilarity_search_structure_local",
    ]


def test_the_sweep_labels_a_missing_program():
    sweep = _module("scripts/test_all_tools.py", "tat_bin")

    label = sweep._format_result_status(
        sweep.normalize_result(
            {"skipped": 2, "skipped_missing_binary": 2, "tests_run": 0}
        )
    )

    assert "need a program this host does not have" in label
    assert "credential" not in label


def test_a_category_with_no_examples_is_not_called_a_credential_problem():
    """geant4 ships one tool and no examples; it was reported as needing a key."""
    sweep = _module("scripts/test_all_tools.py", "tat_noex")

    label = sweep._format_result_status(
        sweep.normalize_result(
            {"skipped": 1, "skipped_no_examples": 1, "tests_run": 0}
        )
    )

    assert "ship no test examples to run" in label
    assert "credential" not in label


def test_an_agentic_tool_without_a_provider_is_not_called_a_credential_problem():
    sweep = _module("scripts/test_all_tools.py", "tat_llm")

    label = sweep._format_result_status(
        sweep.normalize_result(
            {"skipped": 1, "skipped_llm_provider": 1, "tests_run": 0}
        )
    )

    assert "LLM_PROVIDER_WORKING=1" in label
    assert "credential" not in label


def test_a_skip_with_no_name_of_its_own_is_still_a_credential():
    sweep = _module("scripts/test_all_tools.py", "tat_cred")

    label = sweep._format_result_status(
        sweep.normalize_result({"skipped": 1, "tests_run": 0})
    )

    assert "need a credential this run does not have" in label


def test_every_reason_is_counted_once_when_they_mix():
    sweep = _module("scripts/test_all_tools.py", "tat_mix")

    label = sweep._format_result_status(
        sweep.normalize_result(
            {
                "skipped": 6,
                "skipped_missing_package": 1,
                "skipped_missing_binary": 1,
                "skipped_local_input": 1,
                "skipped_long_running": 1,
                "skipped_no_examples": 1,
                "tests_run": 0,
            }
        )
    )

    assert "1 need a package that is not installed" in label
    assert "1 need a program this host does not have" in label
    assert "1 need an input file the caller supplies" in label
    assert "poll an upstream job" in label
    assert "1 ship no test examples to run" in label
    # One skip is left unaccounted, and only that one is a credential.
    assert "1 need a credential this run does not have" in label


def test_the_sweep_parses_the_new_counters_from_the_runner_output():
    """The runner prints them; the sweep must read them back."""
    sweep = _module("scripts/test_all_tools.py", "tat_parse")

    stats = sweep.parse_test_output(
        "Skipped:          3\n"
        "Skipped missing binary: 1\n"
        "Skipped no examples: 1\n"
        "Skipped llm provider: 1\n"
    )

    assert stats["skipped"] == 3
    assert stats["skipped_missing_binary"] == 1
    assert stats["skipped_no_examples"] == 1
    assert stats["skipped_llm_provider"] == 1


def test_tu_info_names_the_program_to_install():
    """`tu info` showed required_packages or required_api_keys, never both, and
    never a binary -- so it could not tell a caller to install mmseqs."""
    from tooluniverse.cli import _render_info

    rendered = _render_info(
        {
            "name": "ProteinSimilarity_search_sequence_local",
            "description": "d",
            "required_binaries": [
                {"name": "mmseqs", "env_var": "TOOLUNIVERSE_MMSEQS2_BINARY"}
            ],
        }
    )

    assert "mmseqs (or $TOOLUNIVERSE_MMSEQS2_BINARY)" in rendered


def test_tu_info_shows_a_package_and_a_credential_together():
    """They were joined with `or`, so only the first of the two was shown."""
    from tooluniverse.cli import _render_info

    rendered = _render_info(
        {
            "name": "t",
            "description": "d",
            "required_packages": ["pyarrow"],
            "required_api_keys": ["FDA_API_KEY"],
        }
    )

    assert "pyarrow" in rendered
    assert "FDA_API_KEY" in rendered
