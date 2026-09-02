"""Regression tests for Python executor sandbox and subprocess behavior."""

import json
import time
from concurrent.futures import ThreadPoolExecutor
from importlib import metadata as importlib_metadata
from pathlib import Path

import pytest

from tooluniverse.python_executor_tool import PythonCodeExecutor, PythonScriptRunner

pytestmark = pytest.mark.unit


def _code_executor():
    return PythonCodeExecutor({"name": "python_code_executor"})


def _script_runner():
    return PythonScriptRunner({"name": "python_script_runner"})


def test_allowed_imports_is_not_exposed_in_tool_schema():
    """The MCP schema must not advertise caller-controlled import permissions."""
    config_path = (
        Path(__file__).parents[2]
        / "src"
        / "tooluniverse"
        / "data"
        / "python_executor_tools.json"
    )
    config = json.loads(config_path.read_text())

    assert "allowed_imports" not in config[0]["parameter"]["properties"]


def test_caller_allowed_imports_is_rejected_explicitly():
    """Legacy calls that bypass schema validation must receive a clear error."""
    result = _code_executor().run(
        {
            "code": "import time\nresult = time.time()",
            "allowed_imports": ["time"],
        }
    )

    assert result["status"] == "error"
    assert result["data"]["error_type"] == "SecurityError"
    assert "cannot be set per call" in result["data"]["error"]


def test_allowed_package_submodules_are_importable():
    """Allowlisting a package must also allow its internal submodules."""
    executor = _code_executor()
    safe_import = executor._create_safe_globals()["__builtins__"]["__import__"]

    imported = safe_import("numpy._core._methods")

    assert imported.__name__ == "numpy"


def test_module_prefix_must_end_at_package_boundary():
    """A package-name prefix without a dot must not bypass the allowlist."""
    executor = _code_executor()
    safe_import = executor._create_safe_globals()["__builtins__"]["__import__"]

    with pytest.raises(ImportError, match="is not allowed"):
        safe_import("numpymalicious")


def test_dangerous_allowed_package_submodule_remains_blocked():
    """Package-prefix matching must not expose an FFI sandbox escape."""
    executor = _code_executor()
    safe_import = executor._create_safe_globals()["__builtins__"]["__import__"]

    with pytest.raises(ImportError, match="is not allowed"):
        safe_import("numpy.ctypeslib")


@pytest.mark.parametrize(
    "code",
    [
        "from numpy import ctypeslib\nresult = 1",
        "from numpy.ctypeslib import load_library\nresult = 1",
        "from random import _os\nresult = _os.name",
        "from collections import _sys\nresult = 1",
    ],
)
def test_dangerous_from_imports_are_blocked(code):
    """ImportFrom aliases must not bypass dangerous module-pivot checks."""
    result = _code_executor().run({"code": code})

    assert result["status"] == "error"
    assert result["data"]["error_type"] == "SecurityError"
    assert "Forbidden import" in result["data"]["error"]


def test_wildcard_from_import_is_blocked():
    """Wildcard imports must not inject unvalidated dangerous module aliases."""
    result = _code_executor().run(
        {"code": "from numpy import *\nresult = int(array([1, 2]).sum())"}
    )

    assert result["status"] == "error"
    assert result["data"]["error_type"] == "SecurityError"
    assert "Forbidden wildcard import" in result["data"]["error"]


@pytest.mark.parametrize(
    "code, expected",
    [
        ("from numpy import array\nresult = int(array([1, 2]).sum())", 3),
        ("from numpy._core import _methods\nresult = 1", 1),
    ],
)
def test_safe_from_imports_still_work(code, expected):
    """The ImportFrom hardening must preserve ordinary scientific imports."""
    result = _code_executor().run({"code": code})

    assert result["status"] == "success", result["data"].get("error")
    assert result["data"]["result"] == expected


def test_script_runner_completes_and_captures_output(tmp_path):
    """A trivial script must exit promptly and return its stdout."""
    script = tmp_path / "trivial.py"
    script.write_text('print("hello")\n')

    started = time.monotonic()
    result = _script_runner().run(
        {
            "script_path": str(script),
            "working_directory": str(tmp_path),
            "timeout": 5,
        }
    )

    assert time.monotonic() - started < 5
    assert result["status"] == "success"
    assert result["data"]["stdout"] == "hello\n"


def test_script_runner_returns_partial_output_on_timeout(tmp_path):
    """Output flushed before a timeout must be returned to the caller."""
    script = tmp_path / "timeout.py"
    script.write_text(
        "import sys\n"
        "import time\n"
        'print("stdout-before-timeout", flush=True)\n'
        'print("stderr-before-timeout", file=sys.stderr, flush=True)\n'
        "time.sleep(10)\n"
    )

    result = _script_runner().run(
        {
            "script_path": str(script),
            "working_directory": str(tmp_path),
            "timeout": 0.2,
        }
    )

    assert result["status"] == "error"
    assert result["data"]["error_type"] == "TimeoutError"
    assert result["data"]["stdout"] == "stdout-before-timeout\n"
    assert result["data"]["stderr"] == "stderr-before-timeout\n"


def test_script_runner_preserves_output_on_nonzero_exit(tmp_path):
    """A failed child must still return both diagnostic output streams."""
    script = tmp_path / "failure.py"
    script.write_text(
        "import sys\n"
        'print("stdout-before-failure")\n'
        'print("stderr-before-failure", file=sys.stderr)\n'
        "raise SystemExit(7)\n"
    )

    result = _script_runner().run(
        {
            "script_path": str(script),
            "working_directory": str(tmp_path),
            "timeout": 5,
        }
    )

    assert result["status"] == "error"
    assert result["data"]["error_type"] == "RuntimeError"
    assert result["data"]["stdout"] == "stdout-before-failure\n"
    assert result["data"]["stderr"] == "stderr-before-failure\n"


def test_subprocess_output_keeps_text_mode_newline_normalization(tmp_path):
    """File-backed capture must retain the old text-mode newline behavior."""
    capture_path = tmp_path / "capture.bin"
    capture_path.write_bytes(b"first\r\nsecond\rthird\n")

    with capture_path.open("rb") as capture:
        output = PythonScriptRunner._read_subprocess_output(capture)

    assert output == "first\nsecond\nthird\n"


def test_script_runner_handles_output_larger_than_pipe_buffers(tmp_path):
    """Large stdout/stderr payloads must complete without a pipe deadlock."""
    script = tmp_path / "large_output.py"
    script.write_text(
        'import sys\nsys.stdout.write("x" * 262144)\nsys.stderr.write("y" * 262144)\n'
    )

    result = _script_runner().run(
        {
            "script_path": str(script),
            "working_directory": str(tmp_path),
            "timeout": 5,
        }
    )

    assert result["status"] == "success"
    assert result["data"]["stdout"] == "x" * 262144
    assert result["data"]["stderr"] == "y" * 262144


def test_script_runner_supports_concurrent_calls(tmp_path):
    """Concurrent runner calls must keep captures isolated and terminate."""
    script = tmp_path / "concurrent.py"
    script.write_text('print("concurrent-output")\n')
    runner = _script_runner()
    arguments = {
        "script_path": str(script),
        "working_directory": str(tmp_path),
        "timeout": 5,
    }

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: runner.run(arguments), range(16)))

    assert all(result["status"] == "success" for result in results)
    assert all(result["data"]["stdout"] == "concurrent-output\n" for result in results)


def test_dependency_check_distinguishes_cpu_and_gpu_distributions(monkeypatch):
    """The CPU distribution must not satisfy an onnxruntime-gpu dependency."""

    def fake_version(distribution_name):
        if distribution_name == "onnxruntime":
            return "1.28.0"
        raise importlib_metadata.PackageNotFoundError(distribution_name)

    monkeypatch.setattr(importlib_metadata, "version", fake_version)

    result = _code_executor()._check_and_install_dependencies(
        ["onnxruntime-gpu"], auto_install=False, require_confirmation=True
    )

    assert result["success"] is False
    assert result["missing_packages"] == ["onnxruntime-gpu"]
    assert result["packages_to_install"] == ["onnxruntime-gpu"]


def test_dependency_check_accepts_exact_distribution(monkeypatch):
    """An exact installed distribution name must satisfy the dependency check."""

    def fake_version(distribution_name):
        if distribution_name == "onnxruntime":
            return "1.28.0"
        raise importlib_metadata.PackageNotFoundError(distribution_name)

    monkeypatch.setattr(importlib_metadata, "version", fake_version)

    result = _code_executor()._check_and_install_dependencies(["onnxruntime"])

    assert result["success"] is True


def test_dependency_check_does_not_truncate_dotted_distribution(monkeypatch):
    """An installed parent distribution must not satisfy a dotted name."""

    def fake_version(distribution_name):
        if distribution_name == "example":
            return "1.0.0"
        raise importlib_metadata.PackageNotFoundError(distribution_name)

    monkeypatch.setattr(importlib_metadata, "version", fake_version)

    result = _code_executor()._check_and_install_dependencies(
        ["example.plugin"], auto_install=False, require_confirmation=True
    )

    assert result["success"] is False
    assert result["missing_packages"] == ["example.plugin"]
    assert result["packages_to_install"] == ["example.plugin"]
