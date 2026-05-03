#!/usr/bin/env python3
"""
PMC tool compatibility tests

- Schema should not require `limit` (defaults apply).
- `retmax` should be accepted as an alias for `limit`.
"""

import json
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tooluniverse.base_tool import BaseTool
from tooluniverse.pmc_tool import PMCTool


@pytest.mark.unit
class TestPMCToolCompatibility(unittest.TestCase):
    def _load_pmc_tool_config(self) -> dict:
        path = (
            Path(__file__).resolve().parent.parent.parent
            / "src"
            / "tooluniverse"
            / "data"
            / "pmc_tools.json"
        )
        configs = json.loads(path.read_text())
        return next(c for c in configs if c.get("name") == "PMC_search_papers")

    def test_schema_does_not_require_limit(self):
        cfg = self._load_pmc_tool_config()
        required = cfg.get("parameter", {}).get("required", [])
        self.assertIn("query", required)
        self.assertNotIn("limit", required)

        tool = BaseTool(cfg)
        self.assertIsNone(tool.validate_parameters({"query": "epistasis"}))
        self.assertIsNone(tool.validate_parameters({"query": "epistasis", "retmax": 5}))

    def test_retmax_alias_is_used(self):
        tool = PMCTool()

        captured = {}

        def fake_search(**kwargs):
            captured.update(kwargs)
            return []

        with patch.object(tool, "_search", side_effect=fake_search):
            tool.run({"query": "marginal epistasis", "retmax": 7})

        self.assertEqual(captured.get("limit"), 7)

