"""Unit tests for DeepSpotMTool.

DeepSpot-M's weights are gated on the Hugging Face Hub and the `deepspotm`
package is an optional dependency, so none of these tests may install it,
download anything, or reach the network. Every test here therefore exercises
the paths that run *before* the model is touched: argument validation, tile
geometry, and the actionable error the tool must produce when the optional
dependency is absent.
"""

import json
from pathlib import Path

import pytest

from tooluniverse.deepspotm_tool import SOURCES, TILE_SIZE, DeepSpotMTool

pytestmark = pytest.mark.unit

_DATA_DIR = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data"
_TOOL_NAME = "DeepSpotM_predict_gene_expression"


def _config():
    configs = json.loads((_DATA_DIR / "deepspotm_tools.json").read_text())
    for cfg in configs:
        if cfg["name"] == _TOOL_NAME:
            return cfg
    raise AssertionError(f"{_TOOL_NAME} not found in deepspotm_tools.json")


@pytest.fixture
def tool():
    return DeepSpotMTool(tool_config=_config())


def _tile(tmp_path, size=(TILE_SIZE, TILE_SIZE), name="tile.png"):
    """Write a small RGB image and return its path."""
    Image = pytest.importorskip("PIL.Image", reason="Pillow not installed")
    path = tmp_path / name
    Image.new("RGB", size, (200, 150, 180)).save(path)
    return str(path)


# -- configuration ------------------------------------------------------


def test_config_declares_optional_dependency_and_local_input():
    """The harness skips execution only if these two flags are set.

    Without them, scripts/test_new_tools.py would try to run the tool against
    a placeholder path with `deepspotm` absent, and report a spurious failure.
    """
    cfg = _config()
    assert cfg["type"] == "DeepSpotMTool"
    assert cfg["requires_local_input"] is True
    assert cfg["required_packages"] == ["deepspotm"]
    assert cfg["parameter"]["required"] == ["image_path", "genes"]


def test_config_enumerates_exactly_the_supported_sources():
    """A drift between the JSON enum and the module constant would let the
    schema accept a source that run() then rejects."""
    cfg = _config()
    assert set(cfg["parameter"]["properties"]["source"]["enum"]) == set(SOURCES)


def test_description_states_predictions_are_not_measurements():
    """These values are model output, not assay output. An agent reading only
    the tool description must not be able to mistake them for ground truth."""
    description = _config()["description"].lower()
    assert "predicted" in description
    assert (
        "not measured" in description or "not be treated as ground-truth" in description
    )


# -- construction -------------------------------------------------------


def test_constructing_the_tool_never_touches_the_network(tool):
    """The model is loaded lazily, so construction must succeed with the
    optional dependency absent and without contacting Hugging Face."""
    assert tool._models == {}


# -- argument validation ------------------------------------------------


def test_missing_image_path_is_rejected(tool):
    """An agent that forgets the tile path gets told which field is missing."""
    result = tool.run({"genes": ["EPCAM"]})
    assert result["status"] == "error"
    assert "image_path" in result["error"]


def test_missing_genes_is_rejected(tool, tmp_path):
    """Genes are mandatory: the full ~19k panel is never returned in one call."""
    result = tool.run({"image_path": _tile(tmp_path)})
    assert result["status"] == "error"
    assert "genes" in result["error"]


def test_nonexistent_image_is_rejected(tool):
    """A bad path fails on the path, not later inside the model loader."""
    result = tool.run({"image_path": "/nope/missing.png", "genes": ["EPCAM"]})
    assert result["status"] == "error"
    assert "No such image file" in result["error"]


def test_unknown_source_is_rejected_before_loading(tool, tmp_path):
    """A bad source is caught before the expensive checkpoint load, and the
    error lists the sources that would have worked."""
    result = tool.run(
        {"image_path": _tile(tmp_path), "genes": ["EPCAM"], "source": "nonesuch"}
    )
    assert result["status"] == "error"
    assert "nonesuch" in result["error"]
    for source in SOURCES:
        assert source in result["error"]


def test_unreadable_image_is_reported_clearly(tool, tmp_path):
    """A non-image file is reported as such rather than as a model failure."""
    path = tmp_path / "not_an_image.png"
    path.write_text("this is not a PNG")
    result = tool.run({"image_path": str(path), "genes": ["EPCAM"]})
    assert result["status"] == "error"
    assert "as an image" in result["error"]


# -- tile geometry ------------------------------------------------------


def test_wrong_tile_size_is_rejected_with_the_expected_size(tool, tmp_path):
    """A tile at the wrong scale degrades predictions silently, and the scale
    cannot be recovered from the pixels, so the one check available -- the
    pixel dimensions -- has to be enforced rather than warned about."""
    result = tool.run(
        {
            "image_path": _tile(tmp_path, size=(512, 512), name="big.png"),
            "genes": ["EPCAM"],
        }
    )
    assert result["status"] == "error"
    assert "512x512" in result["error"]
    assert f"{TILE_SIZE}x{TILE_SIZE}" in result["error"]


# -- optional dependency ------------------------------------------------


def test_missing_package_yields_an_actionable_error(tool, tmp_path):
    """With `deepspotm` absent the tool must say how to install it and how to
    get access to the gated weights, not raise an opaque ImportError."""
    pytest.importorskip("PIL.Image", reason="Pillow not installed")
    try:
        import deepspotm  # noqa: F401
    except ImportError:
        pass
    else:
        pytest.skip("deepspotm is installed; the missing-package path cannot run")

    result = tool.run({"image_path": _tile(tmp_path), "genes": ["EPCAM"]})
    assert result["status"] == "error"
    assert "pip install deepspotm" in result["error"]
    assert "huggingface" in result["error"].lower()
    assert result.get("retriable") is False
