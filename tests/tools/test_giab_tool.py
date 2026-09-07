"""Tests for the GIAB (Genome in a Bottle) benchmark file browser tool.

GIAB has no JSON API -- only a plain Apache directory listing -- so this
tool parses that listing to navigate the benchmark release tree. These
tests exercise the parsing against the live tree, not a mock, since the
whole point of the tool is correctly reflecting that tree's structure.
"""

import pytest
from tooluniverse import ToolUniverse


TRANSIENT = ("timed out", "Failed to connect", "HTTP 5")

HG002_GRCH38_V421 = "AshkenazimTrio/HG002_NA24385_son/NISTv4.2.1/GRCh38"


@pytest.fixture(scope="module")
def tu():
    instance = ToolUniverse()
    instance.load_tools()
    return instance


def data_of(result):
    if result.get("status") == "error":
        error = str(result.get("error", ""))
        if any(t in error for t in TRANSIENT):
            pytest.skip(f"upstream temporarily unavailable: {error[:80]}")
        pytest.fail(f"unexpected error response: {error[:200]}")
    return result["data"]


class TestRegistration:
    def test_tool_loads(self, tu):
        names = {t.get("name") for t in tu.all_tools if isinstance(t, dict)}
        assert "GIAB_list_directory" in names


class TestListDirectory:
    def test_top_level_lists_known_trios(self, tu):
        entries = data_of(tu.tools.GIAB_list_directory())
        names = {e["name"] for e in entries}
        assert "AshkenazimTrio" in names
        assert "NA12878_HG001" in names
        assert all(e["type"] == "directory" for e in entries)

    def test_directory_names_have_no_trailing_slash(self, tu):
        entries = data_of(tu.tools.GIAB_list_directory())
        assert all(not e["name"].endswith("/") for e in entries)

    def test_benchmark_files_present_with_urls_and_sizes(self, tu):
        entries = data_of(tu.tools.GIAB_list_directory(path=HG002_GRCH38_V421))
        files = {e["name"]: e for e in entries if e["type"] == "file"}
        vcf_name = "HG002_GRCh38_1_22_v4.2.1_benchmark.vcf.gz"
        assert vcf_name in files
        vcf = files[vcf_name]
        assert vcf["url"].startswith("https://ftp-trace.ncbi.nlm.nih.gov/")
        assert vcf["url"].endswith(vcf_name)
        assert vcf["size"]

    def test_default_path_is_top_level(self, tu):
        default_entries = data_of(tu.tools.GIAB_list_directory())
        explicit_entries = data_of(tu.tools.GIAB_list_directory(path=""))
        assert {e["name"] for e in default_entries} == {
            e["name"] for e in explicit_entries
        }

    def test_path_traversal_rejected(self, tu):
        result = tu.tools.GIAB_list_directory(path="../../../etc")
        assert result["status"] == "error"

    def test_nonexistent_path(self, tu):
        result = tu.tools.GIAB_list_directory(path="NotARealGIABPath123")
        assert result["status"] == "error"


class TestErrorHandling:
    def test_returns_error_dict_not_exception(self, tu):
        result = tu.tools.GIAB_list_directory(path="../x")
        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert isinstance(result.get("error"), str) and result["error"]
