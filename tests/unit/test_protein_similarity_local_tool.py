import json
import os
from pathlib import Path
import shutil
import signal
import subprocess

import pytest
from jsonschema import validate

from tooluniverse.protein_similarity_local_tool import (
    LocalProteinSimilarityTool,
    _fasta_queries,
    _execute,
    _parse,
    _pdb_queries,
)

DATA = Path(__file__).parents[2] / "src/tooluniverse/data"
CONFIGS = json.loads((DATA / "protein_similarity_local_tools.json").read_text())
MODULE = "tooluniverse.protein_similarity_local_tool"
pytestmark = pytest.mark.unit


def config(operation):
    return next(c for c in CONFIGS if c["fields"]["operation"] == operation)


def test_public_queries_match():
    """Bundled query sequence and coordinates represent the same public protein."""
    lengths, _ = _fasta_queries(DATA / "protein_similarity_1ubq.fasta")
    assert list(lengths.values()) == [76]
    assert (
        _pdb_queries(DATA / "protein_similarity_1ubq.pdb")[0]["protein_CA_residues"]
        == 76
    )


@pytest.mark.parametrize(
    "content",
    ["AAAA", ">a\nAAAA\n>a\nCCCC", ">a\nAA*", ">a\nAA--", ">a\naa", ">a\n", ">\nAAAA"],
)
def test_invalid_fasta_rejected(tmp_path, content):
    """Invalid protein FASTA must fail before alignment."""
    path = tmp_path / "query.fasta"
    path.write_text(content)
    with pytest.raises(ValueError):
        _fasta_queries(path)


def test_query_count_bound(tmp_path):
    """Bound the number of proteins rather than allowing unbounded backend work."""
    path = tmp_path / "query.fasta"
    path.write_text("".join(f">q{i}\nAAAA\n" for i in range(51)))
    with pytest.raises(ValueError, match="50"):
        _fasta_queries(path)


@pytest.mark.parametrize(
    "change",
    [
        "duplicate",
        "alternate",
        "nonfinite",
        "two_chains",
        "two_models",
        "nonstandard",
        "nonstandard_partner",
    ],
)
def test_structure_queries_reject_ambiguous_input(tmp_path, change):
    """Reject ambiguous CA identities and unintended receptor chains."""
    lines = (DATA / "protein_similarity_1ubq.pdb").read_text().splitlines()
    ca = next(i for i, line in enumerate(lines) if line[12:16].strip() == "CA")
    if change == "duplicate":
        lines.insert(ca, lines[ca])
    if change == "alternate":
        lines[ca] = lines[ca][:16] + "A" + lines[ca][17:]
    if change == "nonfinite":
        lines[ca] = lines[ca][:30] + "     nan" + lines[ca][38:]
    if change == "two_chains":
        lines[ca] = lines[ca][:21] + "B" + lines[ca][22:]
    if change == "two_models":
        lines = ["MODEL        1", *lines, "ENDMDL", "MODEL        2", *lines, "ENDMDL"]
    if change == "nonstandard":
        lines[ca] = lines[ca][:17] + "MSE" + lines[ca][20:]
    if change == "nonstandard_partner":
        lines.append(lines[ca][:17] + "HIE B" + lines[ca][22:])
    path = tmp_path / "query.pdb"
    path.write_text("\n".join(lines) + "\n")
    with pytest.raises(ValueError):
        _pdb_queries(path)


def test_parse_keeps_fraction_units_and_reports_truncation(tmp_path):
    """Preserve native fraction units and count all rows before output clipping."""
    path = tmp_path / "hits.tsv"
    path.write_text(
        "q\tx\t0.4\t50\t1\t50\t76\t5\t54\t100\t0.001\t30\t0.658\t0.5\nq\ty\t0.3\t60\t2\t61\t76\t1\t60\t60\t0.00001\t40\t0.789\t1.0\n"
    )
    hits, total = _parse(path, "sequence", 1, {"q": 76})
    assert total == 2 and len(hits) == 1 and hits[0]["target"] == "y"
    assert hits[0]["fident"] == 0.3


@pytest.mark.parametrize(
    "field,value",
    [(2, "nan"), (2, "35"), (3, "50.5"), (4, "0"), (5, "100"), (10, "-1"), (12, "1.5")],
)
def test_malformed_output_is_failure(tmp_path, field, value):
    """Malformed alignments must not become an empty successful search."""
    row = "q x 0.4 50 1 50 76 5 54 100 0.001 30 0.658 0.5".split()
    row[field] = value
    path = tmp_path / "hits.tsv"
    path.write_text("\t".join(row) + "\n")
    with pytest.raises(ValueError):
        _parse(path, "sequence", 20, {"q": 76})


def test_unreturned_rows_are_also_identity_checked(tmp_path):
    """Validate query identity even in rows that will not be returned."""
    path = tmp_path / "hits.tsv"
    path.write_text(
        "q\tx\t0.4\t50\t1\t50\t76\t5\t54\t100\t0.001\t40\t0.658\t0.5\nq\ty\t0.3\t60\t2\t61\t77\t1\t60\t60\t0.001\t20\t0.779\t1.0\n"
    )
    with pytest.raises(ValueError, match="lengths"):
        _parse(path, "sequence", 1, {"q": 76})


@pytest.mark.parametrize("field", ["query_TM", "target_TM", "query_length"])
def test_structure_output_bounds_and_identity(tmp_path, field):
    """Exact normalized TM scores and structure query lengths must be validated."""
    row = "q x 1.0 1.0 76 1 76 76 1 76 76 1.0 1.0 1.0".split()
    if field == "query_TM":
        row[2] = "1.013"
    if field == "target_TM":
        row[3] = "1.013"
    if field == "query_length":
        row[7] = "77"
    path = tmp_path / "hits.tsv"
    path.write_text("\t".join(row) + "\n")
    with pytest.raises(ValueError):
        _parse(path, "structure", 20, {"q": 76})


@pytest.mark.parametrize(
    "arguments",
    [
        {},
        {"query_path": "builtin:1UBQ", "reference_path": "/missing"},
        {
            "query_path": "builtin:1UBQ",
            "reference_path": "builtin:1UBQ",
            "threads": True,
        },
        {
            "query_path": "builtin:1UBQ",
            "reference_path": "builtin:1UBQ",
            "minimum_query_coverage": float("nan"),
        },
    ],
)
def test_input_errors_before_binary(tmp_path, monkeypatch, arguments):
    """Invalid caller arguments must not start a local executable."""
    monkeypatch.setattr(
        MODULE + "._execute",
        lambda *a: pytest.fail("Invalid inputs reached subprocess"),
    )
    result = LocalProteinSimilarityTool(config("sequence")).run(arguments)
    assert result["status"] == "error" and result["stage"] == "input_validation"


def test_missing_binary_is_error(monkeypatch):
    """Missing optional software is a dependency failure, not no hits."""
    monkeypatch.delenv("TOOLUNIVERSE_MMSEQS2_BINARY", raising=False)
    monkeypatch.setattr(MODULE + ".shutil.which", lambda *a: None)
    result = LocalProteinSimilarityTool(config("sequence")).run(
        {"query_path": "builtin:1UBQ", "reference_path": "builtin:1UBQ"}
    )
    assert result["stage"] == "dependency_check" and result["status"] == "error"
    validate(result, config("sequence")["return_schema"])


@pytest.mark.parametrize("operation", ["sequence", "structure"])
def test_direct_call_schema_and_staged_inputs(tmp_path, monkeypatch, operation):
    """Native command assembly and response envelopes stay consistent."""
    binary = tmp_path / "binary"
    binary.write_text("public-test-binary")
    binary.chmod(0o755)
    variable = (
        "TOOLUNIVERSE_MMSEQS2_BINARY"
        if operation == "sequence"
        else "TOOLUNIVERSE_FOLDSEEK_BINARY"
    )
    monkeypatch.setenv(variable, str(binary))
    commands = []

    def execute(argv, folder, timeout):
        commands.append(argv)
        log = folder / "process.log"
        log.write_text("public-test-version")
        if argv[1] == "easy-search":
            assert str(folder) in str(argv[2])
            Path(argv[4]).write_text("")
        return log

    monkeypatch.setattr(MODULE + "._execute", execute)
    result = LocalProteinSimilarityTool(config(operation)).run(
        {"query_path": "builtin:1UBQ", "reference_path": "builtin:1UBQ"}
    )
    assert result["status"] == "success" and result["data"]["hits"] == []
    assert result["data"]["novelty_certified"] is False
    # CPU-only is the environment's job, not an argument's: see
    # test_no_argument_is_passed_that_an_older_native_build_rejects.
    assert "--gpu" not in commands[1]
    if operation == "structure":
        fields = commands[1][commands[1].index("--format-output") + 1]
        assert "alntmscore" not in fields
        assert {"qtmscore", "ttmscore"} <= set(fields.split(","))
        assert commands[1][commands[1].index("--exact-tmscore") + 1] == "1"
    validate(result, config(operation)["return_schema"])


@pytest.mark.parametrize("operation", ["sequence", "structure"])
def test_native_public_control(operation):
    """Exercise the actual optional CPU program with public self-retrieval."""
    variable = (
        "TOOLUNIVERSE_MMSEQS2_BINARY"
        if operation == "sequence"
        else "TOOLUNIVERSE_FOLDSEEK_BINARY"
    )
    name = "mmseqs" if operation == "sequence" else "foldseek"
    if not os.environ.get(variable) and not shutil.which(name):
        pytest.skip("Optional native CPU executable is not installed")
    result = LocalProteinSimilarityTool(config(operation)).run(
        {"query_path": "builtin:1UBQ", "reference_path": "builtin:1UBQ", "threads": 1}
    )
    assert result["status"] == "success", result
    hits = result["data"]["hits"]
    assert hits
    key = "fident" if operation == "sequence" else "qtmscore"
    assert max(h[key] for h in hits) >= 0.999
    validate(result, config(operation)["return_schema"])


@pytest.mark.parametrize("value", [1, "true", [], {}])
def test_cluster_expansion_rejects_non_boolean(value):
    result = LocalProteinSimilarityTool(config("structure")).run(
        {
            "query_path": "builtin:1UBQ",
            "reference_path": "builtin:1UBQ",
            "expand_cluster_members": value,
        }
    )
    assert result["status"] == "error" and result["stage"] == "input_validation"


def test_cluster_expansion_requires_companion_databases(tmp_path, monkeypatch):
    reference = tmp_path / "pdb"
    Path(str(reference) + ".dbtype").write_bytes(bytes(4))
    monkeypatch.setattr(
        MODULE + "._execute",
        lambda *_: pytest.fail("Invalid cluster reference must not launch a backend"),
    )
    result = LocalProteinSimilarityTool(config("structure")).run(
        {
            "query_path": "builtin:1UBQ",
            "reference_path": str(reference),
            "expand_cluster_members": True,
        }
    )
    assert result["status"] == "error" and result["stage"] == "input_validation"
    assert "representative prefix" in result["error"]


def test_cluster_member_option_reaches_native_search(tmp_path, monkeypatch):
    reference = tmp_path / "pdb"
    for suffix in [".dbtype", "_clu.dbtype", "_seq.dbtype"]:
        Path(str(reference) + suffix).write_bytes(bytes(4))
    binary = tmp_path / "foldseek"
    binary.write_text("public-test-binary")
    binary.chmod(0o755)
    monkeypatch.setenv("TOOLUNIVERSE_FOLDSEEK_BINARY", str(binary))
    commands = []

    def execute(argv, directory, timeout):
        commands.append(argv)
        log = directory / "process.log"
        log.write_text("public-test-version")
        if argv[1] == "easy-search":
            Path(argv[4]).write_text(
                "protein_similarity_1ubq\t1ubq_A\t1\t1\t76\t1\t76\t76\t1\t76\t76\t1\t1\t1\n"
            )
        return log

    monkeypatch.setattr(MODULE + "._execute", execute)
    result = LocalProteinSimilarityTool(config("structure")).run(
        {
            "query_path": "builtin:1UBQ",
            "reference_path": str(reference),
            "expand_cluster_members": True,
        }
    )
    assert result["status"] == "success", result
    assert commands[1][commands[1].index("--cluster-search") + 1] == "1"
    assert result["data"]["cluster_members_requested"] is True
    assert result["data"]["hits"][0]["qtmscore"] == 1
    validate(result, config("structure")["return_schema"])


def test_sdk_loading_and_dispatch(monkeypatch, tmp_path):
    """The tool category must load and dispatch through the SDK."""
    from tooluniverse import ToolUniverse

    tu = ToolUniverse(
        tool_files={
            "protein_similarity_local": str(
                DATA / "protein_similarity_local_tools.json"
            )
        },
        keep_default_tools=False,
        hooks_enabled=False,
    )
    tu.load_tools()
    assert hasattr(tu.tools, "ProteinSimilarity_search_sequence_local")
    result = tu.run_one_function(
        {
            "name": "ProteinSimilarity_search_sequence_local",
            "arguments": {"query_path": "/missing", "reference_path": "builtin:1UBQ"},
        },
        use_cache=False,
    )
    assert result["status"] == "error"


@pytest.mark.skipif(os.name != "posix", reason="POSIX owned process group handling")
def test_timeout_only_stops_owned_group(tmp_path, monkeypatch):
    """Timeout cleanup must target only the isolated child process group."""
    killed = []

    class Process:
        pid = 876543
        count = 0

        def wait(self, timeout):
            self.count += 1
            if self.count == 1:
                raise subprocess.TimeoutExpired("local-tool", timeout)

    def spawn(argv, **kwargs):
        assert kwargs["start_new_session"] is True
        assert kwargs["env"]["CUDA_VISIBLE_DEVICES"] == ""
        return Process()

    monkeypatch.setattr(MODULE + ".subprocess.Popen", spawn)
    monkeypatch.setattr(
        MODULE + ".os.killpg", lambda pid, sig: killed.append((pid, sig))
    )
    with pytest.raises(TimeoutError):
        _execute(["local-tool"], tmp_path, 1)
    assert killed == [(876543, signal.SIGKILL)]


def test_query_snapshot_survives_caller_file_change(tmp_path, monkeypatch):
    """An input change after validation must not alter the staged query."""
    query = tmp_path / "query.fasta"
    original = (DATA / "protein_similarity_1ubq.fasta").read_bytes()
    query.write_bytes(original)
    binary = tmp_path / "binary"
    binary.write_text("public-test-binary")
    binary.chmod(0o755)
    monkeypatch.setenv("TOOLUNIVERSE_MMSEQS2_BINARY", str(binary))

    def execute(argv, folder, timeout):
        log = folder / "process.log"
        log.write_text("public-test-version")
        if argv[1] == "version":
            query.write_text(">changed\nAAAA\n")
        else:
            assert Path(argv[2]).read_bytes() == original
            Path(argv[4]).write_text("")
        return log

    monkeypatch.setattr(MODULE + "._execute", execute)
    result = LocalProteinSimilarityTool(config("sequence")).run(
        {"query_path": str(query), "reference_path": "builtin:1UBQ"}
    )
    assert result["status"] == "success"


def test_no_argument_is_passed_that_an_older_native_build_rejects(tmp_path, monkeypatch):
    """`--gpu` exists only from Foldseek 10, and rejecting it looked like a bug.

    Foldseek 9 -- still what several package channels carry -- stops at argument
    parsing with `Unrecognized parameter "--gpu"`, which this tool reported as a
    bare "exited 1" because native logs are deliberately not echoed. CPU-only is
    enforced by the environment, so the flag bought nothing.
    """
    seen = {}
    binary = tmp_path / "binary"
    binary.write_text("public-test-binary")
    binary.chmod(0o755)
    monkeypatch.setenv("TOOLUNIVERSE_FOLDSEEK_BINARY", str(binary))

    def execute(argv, folder, timeout):
        log = folder / "process.log"
        log.write_text("public-test-version")
        if argv[1] != "version":
            seen["argv"] = argv
            Path(argv[4]).write_text("")
        return log

    monkeypatch.setattr(MODULE + "._execute", execute)
    result = LocalProteinSimilarityTool(config("structure")).run(
        {"query_path": "builtin:1UBQ", "reference_path": "builtin:1UBQ"}
    )
    assert result["status"] == "success", result
    assert "--gpu" not in seen["argv"], seen["argv"]


def test_a_native_build_too_old_for_an_argument_says_so(tmp_path):
    """The one native log line worth lifting out, since it names no path."""
    complaint = (
        b"easy-search /tmp/caller/secret.pdb\n"
        b'Unrecognized parameter "--gpu". Did you mean "--gap-open" (Gap open cost)?\n'
    )

    class _Process:
        returncode = 1

        @staticmethod
        def wait(timeout=None):
            return 1

    def popen(*args, **kwargs):
        kwargs["stdout"].write(complaint)
        kwargs["stdout"].flush()
        return _Process()

    import tooluniverse.protein_similarity_local_tool as module

    original = module.subprocess.Popen
    module.subprocess.Popen = popen
    try:
        with pytest.raises(RuntimeError) as raised:
            _execute(["local-tool", "easy-search"], tmp_path, 10)
    finally:
        module.subprocess.Popen = original
    message = str(raised.value)
    assert "--gpu" in message
    assert "older than this tool expects" in message
    # The native log holds the caller's paths; the message must not.
    assert "secret.pdb" not in message


def test_every_parameter_description_reads_as_prose():
    """These descriptions are what an agent reads to choose arguments."""
    import re

    text = (DATA / "protein_similarity_local_tools.json").read_text()
    glued = re.findall(r"\b(?:to|of)[0-9–]\S*", text)
    assert glued == [], glued
