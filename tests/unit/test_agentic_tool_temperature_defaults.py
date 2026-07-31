"""Regression tests for shipped AgenticTool temperature defaults."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tooluniverse.agentic_tool import AgenticTool


pytestmark = pytest.mark.unit

_CONFIG_PATH = (
    Path(__file__).parent.parent.parent
    / "src"
    / "tooluniverse"
    / "data"
    / "agentic_tools.json"
)

EXPECTED_TEMPERATURES = {
    "ScientificTextSummarizer": 0.2,
    "MedicalLiteratureReviewer": 0.2,
    "HypothesisGenerator": 0.8,
    "ExperimentalDesignScorer": 0.1,
    "MedicalTermNormalizer": 0.0,
    "NoveltySignificanceReviewer": 0.2,
    "LiteratureContextReviewer": 0.2,
    "MethodologyRigorReviewer": 0.2,
    "DataAnalysisValidityReviewer": 0.2,
    "ResultsInterpretationReviewer": 0.2,
    "WritingPresentationReviewer": 0.2,
    "ReproducibilityTransparencyReviewer": 0.2,
    "EthicalComplianceReviewer": 0.2,
    "QuestionRephraser": 0.2,
    "ProtocolOptimizer": 0.2,
    "AdvancedCodeQualityAnalyzer": 0.1,
    "DomainExpertValidator": 0.1,
    "ToolQualityEvaluator": 0.1,
    "LabelGenerator": 0.1,
    "call_agentic_human": 0.7,
    "ToolMetadataGenerator": 0.1,
    "ToolMetadataStandardizer": 0.0,
    "ToolRelationshipDetector": 0.1,
}


def _configs_by_name():
    configs = json.loads(_CONFIG_PATH.read_text())
    return {config["name"]: config for config in configs}


def test_every_shipped_agent_has_an_intentional_temperature_default():
    configs = _configs_by_name()

    assert set(configs) == set(EXPECTED_TEMPERATURES)
    assert {
        name: config["configs"].get("temperature")
        for name, config in configs.items()
    } == EXPECTED_TEMPERATURES


@pytest.mark.parametrize(
    ("tool_name", "expected"),
    [
        ("MedicalTermNormalizer", 0.0),
        ("ExperimentalDesignScorer", 0.1),
        ("HypothesisGenerator", 0.8),
    ],
)
def test_agentic_tool_uses_shipped_temperature(tool_name, expected, monkeypatch):
    monkeypatch.delenv("TOOLUNIVERSE_LLM_TEMPERATURE", raising=False)
    monkeypatch.delenv("TOOLUNIVERSE_LLM_CONFIG_MODE", raising=False)
    config = _configs_by_name()[tool_name]

    with patch.object(AgenticTool, "_try_initialize_api"):
        tool = AgenticTool(config)

    assert tool._temperature == expected


def test_env_override_can_replace_shipped_temperature(monkeypatch):
    monkeypatch.setenv("TOOLUNIVERSE_LLM_CONFIG_MODE", "env_override")
    monkeypatch.setenv("TOOLUNIVERSE_LLM_TEMPERATURE", "0.55")
    config = _configs_by_name()["ExperimentalDesignScorer"]

    with patch.object(AgenticTool, "_try_initialize_api"):
        tool = AgenticTool(config)

    assert tool._temperature == 0.55
