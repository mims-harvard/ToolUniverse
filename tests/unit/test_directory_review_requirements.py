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
        for match in re.findall(
            r"([\d,]{3,})\+?\s+(?:scientific\s+)?(?:research\s+)?tools", text
        )
    ]


@pytest.mark.parametrize(
    "label, text",
    [
        ("mcpb/manifest.json", MANIFEST["description"]),
        ("server.json", json.dumps(SERVER_JSON)),
        (".claude-plugin/marketplace.json", json.dumps(MARKETPLACE)),
        # README is the listing most people read, and it was the one left out:
        # the three JSON listings were corrected to 2,700 while README still
        # said "1000+ tools" -- under half the catalogue.
        ("README.md", (REPO / "README.md").read_text()),
        # The Codex plugin manifest was the last one still on "1000+ tools".
        (
            "plugins/tooluniverse/.codex-plugin/plugin.json",
            (REPO / "plugins/tooluniverse/.codex-plugin/plugin.json").read_text(),
        ),
        (
            "plugin/.claude-plugin/plugin.json",
            (REPO / "plugin/.claude-plugin/plugin.json").read_text(),
        ),
        # The two plugin READMEs were missed by a hand-written replacement list
        # that only globbed the three skills/ trees.
        ("plugin/README.md", (REPO / "plugin/README.md").read_text()),
        (
            "plugins/tooluniverse/README.md",
            (REPO / "plugins/tooluniverse/README.md").read_text(),
        ),
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


# ── The same drift, in the skill counts and the plugin version ───────────────


def _skill_count():
    """Skills the Claude Code plugin actually ships."""
    return len(list((REPO / "plugin" / "skills").glob("*/SKILL.md")))


def _advertised_skill_floors(text):
    """Every "N+ skills" style claim in a listing string."""
    return [
        int(match.replace(",", ""))
        for match in re.findall(r"([\d,]{2,})\+?\s+(?:research\s+)?skills", text)
    ]


@pytest.mark.parametrize(
    "label, text",
    [
        (".claude-plugin/marketplace.json", json.dumps(MARKETPLACE)),
        (
            "skills/tooluniverse-claude-code-plugin/SKILL.md",
            (REPO / "skills/tooluniverse-claude-code-plugin/SKILL.md").read_text(),
        ),
    ],
)
def test_a_listing_never_advertises_more_skills_than_exist_nor_far_fewer(label, text):
    """The tool counts had a guard and the skill counts did not.

    marketplace.json said "140+ research skills" and the plugin skill said
    "120+", against 163 shipped -- the same undersell the tool-count guard was
    written for, one field over.
    """
    actual = _skill_count()
    floors = _advertised_skill_floors(text)
    assert floors, f"{label} advertises no skill count; it used to"
    for floor in floors:
        assert floor <= actual, (
            f"{label} advertises {floor} skills but the plugin ships {actual}"
        )
        assert floor >= actual * 0.8, (
            f"{label} advertises {floor} skills against {actual} shipped -- "
            "stale enough to undersell; round down to the nearest ten"
        )


def _pyproject_version():
    m = re.search(r'^version = "([^"]+)"', (REPO / "pyproject.toml").read_text(), re.M)
    assert m, "pyproject.toml has no version"
    return m.group(1)


@pytest.mark.parametrize(
    "path",
    [
        "plugin/.claude-plugin/plugin.json",
        "plugins/tooluniverse/.codex-plugin/plugin.json",
        ".claude-plugin/marketplace.json",
    ],
)
def test_the_plugin_version_is_the_version_that_was_released(path):
    """A plugin manifest must not name a version the package never shipped.

    These are hand-bumped and have never agreed with the package at a release
    tag -- measured across four:

        v1.5.5   pyproject 1.5.5   plugin 1.5.1   five releases stale
        v1.5.6   pyproject 1.5.6   plugin 1.5.1   six
        v1.5.7   pyproject 1.5.7   plugin 1.5.8   a version not yet released
        v1.5.8   pyproject 1.5.8   plugin 1.5.9   likewise

    They agree today only because 1.5.9 shipped and the hand-bump happened to
    be one ahead. Equality is the rule that catches both directions, and the
    bumps toward 1.5.8 and 1.5.9 say matching the package was the intent.
    """
    data = json.loads((REPO / path).read_text())
    # plugin.json carries it at the top level; marketplace.json under metadata.
    version = data.get("version") or (data.get("metadata") or {}).get("version")
    assert version, f"{path} has no version field"
    assert version == _pyproject_version(), (
        f"{path} says {version}, pyproject.toml says {_pyproject_version()}"
    )


# ── The standard that told everyone to write the stale number ────────────────


DOC_STANDARD_FILES = [
    "docs/dev_docs/DOCUMENTATION_STANDARDS.md",
    "docs/dev_docs/VALIDATION_GUIDE.md",
]


@pytest.mark.parametrize("path", DOC_STANDARD_FILES)
def test_the_documentation_standard_names_a_current_tool_count(path):
    """The drift had a source, and it was the style guide.

    Both files carried ``Use `1000+ tools` consistently``, and
    VALIDATION_GUIDE.md shipped ``sed -i 's/[0-9]*+ tools/1000+ tools/g'`` to
    enforce it. Anyone following the documented standard would have undone the
    corrections in #859 -- and now trips the guard above while doing it. So the
    standard is held to the same count as the listings it governs.
    """
    text = (REPO / path).read_text()
    stated = re.findall(r"Use `([\d,]+)\+? tools` consistently", text)
    assert stated, f"{path} no longer states a standard tool count"
    actual = _tool_config_count()
    for figure in stated:
        n = int(figure.replace(",", ""))
        assert n <= actual, f"{path} standardises {n} tools, catalogue has {actual}"
        assert n >= actual * 0.8, (
            f"{path} standardises {n} tools against a catalogue of {actual} -- "
            "this is the text other docs are written from, so it goes stale first"
        )


def test_the_enforcing_sed_rewrites_to_the_standard_figure():
    """The one-liner is the standard in executable form; it must agree."""
    text = (REPO / "docs/dev_docs/VALIDATION_GUIDE.md").read_text()
    seds = re.findall(r"sed -i 's/\[0-9\]\*\+ tools/([\d,]+)\+ tools/g'", text)
    assert seds, "VALIDATION_GUIDE.md no longer ships the normalising sed"
    stated = re.findall(r"Use `([\d,]+)\+? tools` consistently", text)
    assert stated, "VALIDATION_GUIDE.md states no standard count"
    assert set(seds) == set(stated), (
        f"the sed rewrites to {set(seds)} while the standard says {set(stated)}"
    )


# ── A per-key claim is a different quantity, and needs an exact check ────────
#
# The guards above compare a *catalogue* claim against the catalogue, as a
# floor: "an exact count would fail on every tool added", so a listing may
# round down. The bundle's key prompts make a different claim -- how many tools
# a given API key raises the limits for -- and it slipped through all of it:
#
#   mcpb/manifest.json  "Raises NCBI rate limits for 34 tools"   -- 35 of them
#                       "Raises openFDA rate limits for 18 tools"
#
# Nothing checked it, for two reasons. `_advertised_floors` reads only
# MANIFEST["description"], so the user_config prompts were never scanned; and
# its pattern requires three digits or more, so a two-digit claim could not
# have matched even there. The 34 was written in #653 and was never revisited.
#
# A floor is the wrong shape for this one. "35 tools" is a precise statement
# about a small number an operator reads while deciding whether a key is worth
# getting, 80% of it is not a useful answer, and the correction when a tool is
# added is one character in one file. So this is exact.


def _tools_declaring(env_var):
    """Tool configs naming `env_var` in required_api_keys or optional_api_keys."""
    data_dir = REPO / "src" / "tooluniverse" / "data"
    names = set()
    for path in data_dir.glob("*.json"):
        if path.name in {"api_keys_catalog.json", "mcp_contracts.lock.json"}:
            continue
        try:
            entries = json.loads(path.read_text())
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict) or "name" not in entry:
                continue
            for field in ("required_api_keys", "optional_api_keys"):
                declared = entry.get(field)
                if isinstance(declared, list) and env_var in declared:
                    names.add(entry["name"])
    return names


def _env_var_for(user_config_key):
    """The variable the bundle exports from a user_config entry, per the manifest.

    Read from `server.mcp_config.env` rather than by upper-casing the key: the
    mapping is stated in the file, and a prompt whose variable is not exported
    at all is a thing worth failing on rather than guessing about.
    """
    for variable, value in MANIFEST["server"]["mcp_config"]["env"].items():
        if value == "${user_config.%s}" % user_config_key:
            return variable
    return None


def _key_claims():
    """`(user_config key, claimed count)` for every prompt stating a tool count."""
    claims = []
    for key, config in MANIFEST.get("user_config", {}).items():
        for figure in re.findall(r"(\d[\d,]*)\s+tools", config.get("description", "")):
            claims.append((key, int(figure.replace(",", ""))))
    return claims


@pytest.mark.parametrize("key, claimed", _key_claims(), ids=lambda v: str(v))
def test_a_key_prompt_states_exactly_how_many_tools_use_that_key(key, claimed):
    variable = _env_var_for(key)

    assert variable, (
        f"user_config.{key} claims {claimed} tools but the manifest exports no "
        "environment variable for it, so the claim is about nothing"
    )
    actual = len(_tools_declaring(variable))
    assert claimed == actual, (
        f"user_config.{key} says {claimed} tools use {variable}; "
        f"{actual} declare it. Adding a tool that uses this key means updating "
        "this prompt -- it is what a Desktop user reads to decide whether the "
        "key is worth getting."
    )


def test_the_two_prompts_that_carry_a_count_still_carry_one():
    """Dropping the number would make the claim un-checkable rather than wrong.

    Both of these are optional keys whose tools work without them, so the count
    is the whole of what the prompt tells an operator. A new prompt that states
    a count is welcome -- add it here and the test above starts checking it.
    """
    assert {key for key, _ in _key_claims()} == {"ncbi_api_key", "fda_api_key"}
