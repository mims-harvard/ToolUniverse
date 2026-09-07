"""PackageTool's `_get_pypi_info` (backing every `get_<package>_info` tool, e.g.
`get_mne_info`, `get_nilearn_info`) derived three fields incorrectly from the raw
PyPI JSON API response:

- `last_updated` used `last_serial` (PyPI's internal monotonic change-counter,
  currently in the tens of millions) as if it were a Unix timestamp, decoding to
  bogus dates in 1970-1971.
- `python_versions` returned the *entire* `classifiers` list (license, OS, dev
  status, audience, ...) unfiltered, not just the Python version entries.
- `repository` only checked the `Repository`/`Source` project_urls keys, missing
  common variants like `Source Code` (e.g. mne-python) even when `documentation`
  was found fine from the same dict.

Covers the fix with mocked PyPI responses (no live pypi.org calls).
"""

from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


def _make_tool(package_name="mne"):
    from tooluniverse.package_tool import PackageTool

    return PackageTool(
        {
            "name": f"get_{package_name}_info",
            "type": "PackageTool",
            "package_name": package_name,
        }
    )


def _pypi_response(
    classifiers=None,
    requires_python=None,
    project_urls=None,
    upload_time="2026-04-20T17:16:54.447882Z",
    last_serial=36296717,
):
    body = {
        "info": {
            "name": "mne",
            "summary": "MEG and EEG data analysis.",
            "version": "1.12.1",
            "author": "MNE developers",
            "license": "BSD-3-Clause",
            "home_page": "",
            "project_urls": project_urls or {},
            "classifiers": classifiers or [],
            "requires_python": requires_python,
            "keywords": "",
        },
        "last_serial": last_serial,
        "urls": [{"upload_time_iso_8601": upload_time}] if upload_time else [],
    }
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = body
    return resp


class TestLastUpdated:
    def test_uses_real_upload_time_not_last_serial(self):
        tool = _make_tool()
        with patch("tooluniverse.package_tool.requests.get") as get:
            get.return_value = _pypi_response()
            result = tool.run({"source": "pypi", "include_examples": False})
        assert result["last_updated"] == "2026-04-20T17:16:54.447882Z"
        # The bogus 1970s-decoding serial number must not leak into the field.
        assert result["last_updated"] != 36296717

    def test_falls_back_to_unknown_when_no_release_urls(self):
        tool = _make_tool()
        with patch("tooluniverse.package_tool.requests.get") as get:
            get.return_value = _pypi_response(upload_time=None)
            result = tool.run({"source": "pypi", "include_examples": False})
        assert result["last_updated"] == "Unknown"


class TestPythonVersions:
    def test_filters_classifiers_to_python_version_entries(self):
        tool = _make_tool("nilearn")
        classifiers = [
            "Development Status :: 5 - Production/Stable",
            "Intended Audience :: Science/Research",
            "Programming Language :: Python :: 3.10",
            "Programming Language :: Python :: 3.11",
            "Programming Language :: Python :: 3",  # generic, not a real version
            "Topic :: Scientific/Engineering",
        ]
        with patch("tooluniverse.package_tool.requests.get") as get:
            get.return_value = _pypi_response(classifiers=classifiers)
            result = tool.run({"source": "pypi", "include_examples": False})
        assert result["python_versions"] == ["3.10", "3.11"]

    def test_falls_back_to_requires_python_when_no_specific_classifiers(self):
        """mne-python only declares the generic 'Python :: 3' classifier."""
        tool = _make_tool()
        classifiers = ["Programming Language :: Python :: 3"]
        with patch("tooluniverse.package_tool.requests.get") as get:
            get.return_value = _pypi_response(
                classifiers=classifiers, requires_python=">=3.10"
            )
            result = tool.run({"source": "pypi", "include_examples": False})
        assert result["python_versions"] == [">=3.10"]


class TestRepository:
    def test_falls_back_to_source_code_key(self):
        """mne-python's PyPI metadata only sets project_urls['Source Code']."""
        tool = _make_tool()
        with patch("tooluniverse.package_tool.requests.get") as get:
            get.return_value = _pypi_response(
                project_urls={
                    "Documentation": "https://mne.tools/",
                    "Source Code": "https://github.com/mne-tools/mne-python/",
                }
            )
            result = tool.run({"source": "pypi", "include_examples": False})
        assert result["repository"] == "https://github.com/mne-tools/mne-python/"
        assert result["documentation"] == "https://mne.tools/"

    def test_prefers_repository_key_over_alternatives(self):
        tool = _make_tool()
        with patch("tooluniverse.package_tool.requests.get") as get:
            get.return_value = _pypi_response(
                project_urls={
                    "Repository": "https://github.com/example/canonical",
                    "Homepage": "https://example.org",
                }
            )
            result = tool.run({"source": "pypi", "include_examples": False})
        assert result["repository"] == "https://github.com/example/canonical"
