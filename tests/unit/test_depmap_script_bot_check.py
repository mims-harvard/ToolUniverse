"""depmap_gene_dependency.py died with ``KeyError: 'filename'`` on DepMap's bot-check page.

Both documented commands (``gene KRAS ...`` and ``cell-line A375 ...``) crashed because
DepMap's download index now returns an HTML "Verification" page instead of the CSV
file list. The script must say so and explain the manual route (it never tries to get
past the check); files already in the cache directory must work without any request.
"""

import importlib.util
import io
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit

SCRIPT = (
    Path(__file__).parent.parent.parent
    / "skills"
    / "tooluniverse-cell-line-profiling"
    / "scripts"
    / "depmap_gene_dependency.py"
)
HTML = b"<!DOCTYPE html><html><head><title>DepMap - Verification</title></head></html>"


@pytest.fixture
def depmap(tmp_path, monkeypatch):
    monkeypatch.setenv("DEPMAP_CACHE_DIR", str(tmp_path / "cache"))
    spec = importlib.util.spec_from_file_location("depmap_gene_dependency", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class _Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_bot_check_page_raises_a_clear_error_with_the_manual_route(depmap, tmp_path):
    with patch.object(depmap.urllib.request, "urlopen", return_value=_Response(HTML)):
        with pytest.raises(depmap.DepMapUnavailable) as caught:
            depmap._latest_url("CRISPRGeneEffect.csv")
    message = str(caught.value)
    assert "returned a web page instead of the file list" in message
    assert "https://depmap.org/portal/download/all/" in message
    assert str(tmp_path / "cache") in message and "DEPMAP_CACHE_DIR" in message


@pytest.mark.parametrize("argv", [["gene", "KRAS"], ["cell-line", "A375"]])
def test_both_documented_commands_exit_2_with_the_message_not_a_traceback(
    depmap, argv, capsys
):
    with patch.object(depmap.urllib.request, "urlopen", return_value=_Response(HTML)):
        assert depmap.main(argv) == 2
    assert "cannot be fetched automatically" in capsys.readouterr().err


def test_a_real_index_still_resolves_the_newest_public_release(depmap):
    index = (
        "filename,release,url\n"
        "CRISPRGeneEffect.csv,DepMap Public 24Q2,https://x/old\n"
        "CRISPRGeneEffect.csv,DepMap Public 25Q3,https://x/new\n"
        "CRISPRGeneEffect.csv,DepMap Internal 26Q1,https://x/internal\n"
    ).encode()
    with patch.object(depmap.urllib.request, "urlopen", return_value=_Response(index)):
        assert depmap._latest_url("CRISPRGeneEffect.csv") == "https://x/new"


def test_cached_files_are_used_without_contacting_depmap(depmap, tmp_path, capsys):
    pytest.importorskip("pandas")
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "CRISPRGeneEffect.csv").write_text(
        ",KRAS (3845),TP53 (7157)\nACH-1,-1.2,0.1\nACH-2,-0.1,0.0\n"
    )
    (cache / "Model.csv").write_text(
        "ModelID,CellLineName,StrippedCellLineName,OncotreeLineage,OncotreePrimaryDisease\n"
        "ACH-1,A-One,AONE,Pancreas,PDAC\nACH-2,B-Two,BTWO,Lung,NSCLC\n"
    )
    with patch.object(
        depmap.urllib.request, "urlopen", side_effect=AssertionError("network")
    ):
        assert depmap.main(["gene", "KRAS", "--top", "1"]) == 0
    output = capsys.readouterr().out
    assert "AONE" in output and "-1.2" in output
