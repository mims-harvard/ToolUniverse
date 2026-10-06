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
import re
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


# ── Listing metadata must not drift away from the catalogue ──────────────────
#
# PR #667 fixed a manifest that claimed MIT while the repository is Apache-2.0,
# and the same file advertised "2,500+" tools. The licence got a guard; the
# counts did not, and the same stale numbers turned out to be published in two
# more places: server.json (the MCP Registry listing) said "2,500+" and
# "only exposes 4 core tools" when the server exposes five, and
# marketplace.json said "1000+" tools with "115" skills in one sentence and
# "120+" in the next.
#
# An exact count would fail on every tool added, so these check the floor a
# listing advertises is neither above the real catalogue nor far below it.

SERVER_JSON = json.loads((REPO / "server.json").read_text())
MARKETPLACE = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text())
COMPACT_TOOLS = json.loads(
    (REPO / "src" / "tooluniverse" / "data" / "compact_mode_tools.json").read_text()
)


def _tool_config_count():
    """Tools the catalogue actually defines."""
    data_dir = REPO / "src" / "tooluniverse" / "data"
    names = set()
    for path in data_dir.glob("*.json"):
        try:
            entries = json.loads(path.read_text())
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if isinstance(entries, list):
            names.update(
                e["name"] for e in entries if isinstance(e, dict) and "name" in e
            )
    return len(names)


def _advertised_floors(text):
    """Every "N+ tools" style claim in a listing string."""
    return [
        int(match.replace(",", ""))
        for match in re.findall(r"([\d,]{3,})\+?\s+(?:scientific\s+)?(?:research\s+)?tools", text)
    ]


@pytest.mark.parametrize(
    "label, text",
    [
        ("mcpb/manifest.json", MANIFEST["description"]),
        ("server.json", json.dumps(SERVER_JSON)),
        (".claude-plugin/marketplace.json", json.dumps(MARKETPLACE)),
    ],
)
def test_a_listing_never_advertises_more_tools_than_exist_nor_far_fewer(label, text):
    actual = _tool_config_count()
    floors = _advertised_floors(text)
    assert floors, f"{label} advertises no tool count; it used to"
    for floor in floors:
        assert floor <= actual, (
            f"{label} advertises {floor} tools but the catalogue defines {actual}"
        )
        assert floor >= actual * 0.8, (
            f"{label} advertises {floor} tools against a catalogue of {actual} -- "
            "stale enough to undersell the project; round down to the nearest hundred"
        )


def test_the_registry_listing_states_the_number_of_tools_it_exposes():
    """server.json describes compact mode to users of the MCP Registry.

    It said four. ``find_tools`` is registered separately in smcp.py rather
    than in compact_mode_tools.json, so the server exposes one more than that
    file holds -- five. If that registration changes, this is the assertion
    that should be revisited.
    """
    exposed = len(COMPACT_TOOLS) + 1  # + find_tools, registered in smcp.py
    stated = re.search(r"exposes (\d+) core tools", json.dumps(SERVER_JSON))
    assert stated, "server.json no longer states how many tools it exposes"
    assert int(stated.group(1)) == exposed, (
        f"server.json says {stated.group(1)} core tools, the server exposes {exposed}"
    )
