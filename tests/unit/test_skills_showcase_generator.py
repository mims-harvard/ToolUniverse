import pytest

from docs.generate_skills_showcase import categorize_skills, generate_skills_showcase

pytestmark = pytest.mark.unit


def test_remote_tool_hosting_skill_is_setup_configuration():
    """The generic hosting workflow belongs beside the provider setup skills."""
    skill = (
        "host-and-share-remote-tool",
        {"name": "host-and-share-remote-tool", "description": "Share a model."},
    )

    categories = categorize_skills([skill])

    assert categories["Setup & Configuration"] == [skill]
    assert categories["Research Skills"] == []


def test_showcase_includes_remote_tool_hosting_skill():
    """The generated public page links the generic hosting workflow."""
    content = generate_skills_showcase()

    assert "Host and Share a Remote Tool" in content
    assert ":bdg-info:`host-and-share-remote-tool`" in content
