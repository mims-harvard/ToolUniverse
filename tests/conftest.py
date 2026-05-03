import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
import warnings

# ---------------------------------------------------------------------------
# Ensure the source tree is importable even when tests are invoked without
# an editable install.  Several test files duplicated this boilerplate;
# doing it once here avoids the repetition.
# ---------------------------------------------------------------------------
_SRC_PATH = str(Path(__file__).resolve().parents[1] / "src")
if _SRC_PATH not in sys.path:
    sys.path.insert(0, _SRC_PATH)


@pytest.fixture(scope="session", autouse=True)
def _set_test_env() -> None:
    os.environ.setdefault("PYTHONHASHSEED", "0")
    os.environ.setdefault("TOOLUNIVERSE_LIGHT_IMPORT", "1")
    # Avoid accidental network in unit tests unless explicitly marked
    os.environ.setdefault("TOOLUNIVERSE_TESTING", "1")


def pytest_sessionfinish(session, exitstatus):
    """Cleanup cache managers at the end of test session."""
    import gc
    from tooluniverse.cache.result_cache_manager import ResultCacheManager
    
    # Force garbage collection to trigger __del__ methods
    gc.collect()
    
    # Find and cleanup any remaining cache managers
    for obj in gc.get_objects():
        if isinstance(obj, ResultCacheManager):
            try:
                if hasattr(obj, '_worker_thread') and obj._worker_thread is not None:
                    if obj._worker_thread.is_alive():
                        obj.close()
            except Exception:
                pass


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "slow: slow tests (deselect with -m 'not slow')")
    config.addinivalue_line("markers", "require_api_keys: tests requiring API keys")
    config.addinivalue_line("markers", "manual: manual tests (not run in CI)")
    config.addinivalue_line("markers", "unit: unit tests (fast, isolated)")
    config.addinivalue_line("markers", "integration: integration tests (may use network)")


def pytest_collection_modifyitems(items):
    """Ensure test quality by checking for required elements."""
    for item in items:
        # Check for docstring
        if not item.function.__doc__:
            warnings.warn(
                f"Test {item.nodeid} missing docstring - consider adding one",
                category=UserWarning
            )
        
        # Check for appropriate markers
        marks = [m.name for m in item.iter_markers()]
        if not any(m in marks for m in ['unit', 'integration', 'slow', 'manual']):
            warnings.warn(
                f"Test {item.nodeid} missing category marker (unit/integration/slow/manual)",
                category=UserWarning
            )
        
        # Check for meaningful test names
        if not any(keyword in item.name.lower() for keyword in ['test_', 'check_', 'verify_']):
            warnings.warn(
                f"Test {item.nodeid} may not follow naming convention (should start with test_)",
                category=UserWarning
            )


@pytest.fixture(scope="session")
def tools_generated():
    """Ensure tools are generated before running tests."""
    from pathlib import Path
    tools_dir = Path("src/tooluniverse/tools")
    if not tools_dir.exists() or not any(tools_dir.glob("*.py")):
        pytest.fail("Tools not generated. Run: python scripts/build_tools.py")
    return tools_dir


@pytest.fixture(scope="session")
def tooluniverse_instance():
    """Session-scoped ToolUniverse instance for better performance."""
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()
    yield tu
    # Cleanup: ensure cache manager is properly closed
    try:
        if hasattr(tu, 'cache_manager'):
            tu.cache_manager.close()
    except Exception:
        pass


@pytest.fixture
def disable_network(monkeypatch: pytest.MonkeyPatch):
    """Disable network by patching requests' adapters. Use for unit tests."""
    import requests

    def _raise(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("Network disabled in unit test. Use @pytest.mark.integration for network tests.")

    monkeypatch.setattr(requests.sessions.Session, "request", _raise)
    return None


@pytest.fixture
def tmp_workdir(tmp_path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


# ---------------------------------------------------------------------------
# Shared cache-related fixtures (used by test_cache_*, test_tooluniverse_cache_*)
# ---------------------------------------------------------------------------

@pytest.fixture
def memory_cache_manager():
    """Create an in-memory-only ResultCacheManager (no persistence)."""
    from tooluniverse.cache.result_cache_manager import ResultCacheManager

    mgr = ResultCacheManager(
        memory_size=4,
        persistent_path=None,
        enabled=True,
        persistence_enabled=False,
        singleflight=False,
    )
    yield mgr
    mgr.close()


@pytest.fixture
def persistent_cache_manager(tmp_path):
    """Create a ResultCacheManager with SQLite persistence in a temp directory."""
    from tooluniverse.cache.result_cache_manager import ResultCacheManager

    cache_path = str(tmp_path / "cache.sqlite")
    mgr = ResultCacheManager(
        memory_size=4,
        persistent_path=cache_path,
        enabled=True,
        persistence_enabled=True,
        singleflight=False,
    )
    yield mgr
    mgr.close()


@pytest.fixture
def cache_env(tmp_path, monkeypatch):
    """Set cache-related environment variables for the duration of a test.

    Yields the path to the SQLite cache file.
    """
    cache_path = str(tmp_path / "cache.sqlite")
    monkeypatch.setenv("TOOLUNIVERSE_CACHE_ENABLED", "true")
    monkeypatch.setenv("TOOLUNIVERSE_CACHE_PERSIST", "true")
    monkeypatch.setenv("TOOLUNIVERSE_CACHE_MEMORY_SIZE", "4")
    monkeypatch.setenv("TOOLUNIVERSE_CACHE_PATH", cache_path)
    return cache_path


