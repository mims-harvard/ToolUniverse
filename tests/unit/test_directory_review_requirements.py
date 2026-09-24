"""Guards for the two Anthropic connectors-directory rules a submission fails on.

The published review criteria require every tool to carry a ``title`` and the
applicable hint, and require local connectors to ship a privacy policy in three
places -- a README section, a ``privacy_policies`` array in the manifest, and an
HTTPS URL. Anthropic's docs say a missing or incomplete privacy policy is an
immediate rejection, and submissions are a slow manual round trip, so these are
worth failing a build over.

https://claude.com/docs/connectors/building/review-criteria
"""

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO / "src"))

from tooluniverse.tool_defaults import get_annotations_for_tool

pytestmark = pytest.mark.unit

MANIFEST = json.loads((REPO / "mcpb" / "manifest.json").read_text())
COMPACT = json.loads(
    (REPO / "src" / "tooluniverse" / "data" / "compact_mode_tools.json").read_text()
)


def test_manifest_declares_a_privacy_policy_over_https():
    policies = MANIFEST.get("privacy_policies")

    assert policies, "a local connector without privacy_policies is rejected outright"
    for url in policies:
        assert url.startswith("https://"), url


def test_both_readmes_carry_a_privacy_policy_section():
    """The reviewer reads the bundle's README; users read the repo's."""
    for readme in (REPO / "README.md", REPO / "mcpb" / "README.md"):
        assert "## Privacy Policy" in readme.read_text(), readme


def test_the_policy_the_manifest_points_at_exists_and_covers_the_required_topics():
    policy = (REPO / "PRIVACY.md").read_text().lower()

    assert MANIFEST["privacy_policies"][0].endswith("PRIVACY.md")
    for topic in ("collect", "retention", "contact", "third"):
        assert topic in policy, f"policy does not mention {topic}"


@pytest.mark.parametrize("tool", COMPACT, ids=lambda t: t["name"])
def test_every_exposed_tool_declares_a_title_and_a_hint(tool):
    annotations = tool.get("mcp_annotations")

    assert annotations, f"{tool['name']} has no mcp_annotations"
    assert annotations.get("title"), f"{tool['name']} has no title"
    assert "readOnlyHint" in annotations and "destructiveHint" in annotations


def test_the_dispatcher_is_not_advertised_as_read_only():
    """execute_tool reaches every tool in the catalogue, including the ones that
    submit and delete remote jobs. A read-only hint would let those run without
    asking the user."""
    dispatcher = next(t for t in COMPACT if t["name"] == "execute_tool")

    assert dispatcher["mcp_annotations"]["readOnlyHint"] is False
    assert dispatcher["mcp_annotations"]["destructiveHint"] is True


def test_a_declared_title_survives_annotation_resolution():
    """Regression: the resolver rebuilt the annotation dict from the hints alone,
    so a curated title was silently replaced by the tool's own name."""
    resolved = get_annotations_for_tool(
        tool_config={
            "name": "x_get_y",
            "type": "RESTTool",
            "mcp_annotations": {
                "title": "Curated title",
                "readOnlyHint": True,
                "destructiveHint": False,
            },
        }
    )

    assert resolved["title"] == "Curated title"
