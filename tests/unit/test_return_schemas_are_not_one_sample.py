"""Three return_schemas described the one response they were generated from.

A schema built by walking a sample response records that response's *keys*, and
where the keys are data -- a cell index, a citing PMID, an image upload id --
the result validates nothing and ships megabytes to say so.

    eurostat_tools.json       1,860,158 bytes   value: 10,821 numeric keys
                                                status: 1,546 numeric keys
                                                dimension: the 7 dimensions of
                                                the sampled datasets
    openfoodfacts_tools.json    723,717 bytes   images: 147 upload ids +
                                                19 language slots of one product
    icite_tools.json            323,555 bytes   citedByPmidsByYear: 1,720 of
                                                one query's citing PMIDs

Measured: the live Eurostat response for the tool's own first example has 35
keys under `value`, not 10,821 -- the schema did not describe a single one of
them. And since nothing was `required` and `additionalProperties` was open, it
could not fail either: a `value` map holding the string "not-a-number" passed
the old schema and is rejected by the new one.

The replacements describe the formats instead: JSON-stat's index-keyed cell
maps and open dimension set, iCite's {pmid: year} objects, Open Food Facts'
upload-id and language-slot image keys.

This test fails if a schema starts enumerating data as property names again.
"""

import json
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "src" / "tooluniverse" / "data"

# A real vocabulary can be long -- Open Food Facts has 181 nutriment fields and
# 63 ISO country codes -- so the rule is about *numeric* names, which are data
# in every API here. Four is the most any legitimate schema in the tree uses
# (image render widths 100/200/400, Nutri-Score versions 2021/2023).
MAX_NUMERIC_PROPERTY_NAMES = 8


def _numeric_property_blocks(node, path=()):
    if isinstance(node, dict):
        properties = node.get("properties")
        if isinstance(properties, dict):
            numeric = [k for k in properties if re.fullmatch(r"[0-9]+", k)]
            if len(numeric) > MAX_NUMERIC_PROPERTY_NAMES:
                yield "->".join(path) or "root", len(numeric)
        for key, value in node.items():
            yield from _numeric_property_blocks(value, path + (str(key),))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _numeric_property_blocks(value, path + (str(index),))


def _tool_configs():
    for path in sorted(DATA.glob("**/*.json")):
        if "broken_apis" in path.parts:
            continue
        try:
            content = json.loads(path.read_text("utf-8"))
        except ValueError:
            continue
        if not isinstance(content, list):
            continue
        for tool in content:
            if isinstance(tool, dict) and isinstance(tool.get("return_schema"), dict):
                yield path, tool


def test_no_return_schema_enumerates_data_as_property_names():
    offenders = []
    for path, tool in _tool_configs():
        for where, count in _numeric_property_blocks(tool["return_schema"]):
            offenders.append(f"{path.name}:{tool['name']} at {where}: {count} keys")

    assert offenders == [], (
        "a return_schema is enumerating numeric keys from a sample response; "
        "describe the format with patternProperties/additionalProperties "
        "instead:\n  " + "\n  ".join(offenders)
    )


@pytest.mark.parametrize(
    ("file_name", "limit"),
    [
        ("eurostat_tools.json", 60_000),
        ("icite_tools.json", 60_000),
        ("openfoodfacts_tools.json", 400_000),
    ],
)
def test_the_three_files_stay_small(file_name, limit):
    """They were 1.86 MB, 324 KB and 724 KB, all shipped in the wheel."""
    assert (DATA / file_name).stat().st_size < limit


def test_eurostat_describes_json_stat_rather_than_one_dataset():
    tools = json.loads((DATA / "eurostat_tools.json").read_text("utf-8"))
    branch = tools[0]["return_schema"]["oneOf"][0]["properties"]

    assert "^[0-9]+$" in branch["value"]["patternProperties"]
    assert branch["value"]["additionalProperties"] is False
    assert "properties" not in branch["value"]
    # The dimension set belongs to the dataset, not to the API.
    assert "additionalProperties" in branch["dimension"]
    assert "properties" not in branch["dimension"]


def test_icite_search_declares_the_envelope_it_returns():
    """It returns {status, data, metadata} but declared only data and metadata.

    The sweep treats a schema declaring `data` *and* `status` as describing the
    envelope; with `status` absent it unwrapped the envelope and validated the
    bare array against a schema whose top-level type is "object", so all four
    examples passed while the category was reported SCHEMA ERROR.
    """
    tools = json.loads((DATA / "icite_tools.json").read_text("utf-8"))
    tool = next(t for t in tools if t["name"] == "iCite_search_publications")
    properties = tool["return_schema"]["properties"]

    assert set(properties) == {"status", "data", "metadata"}
    # The pagination keys #824 gave this tool were never declared.
    metadata = properties["metadata"]["properties"]
    for key in ("pagination_stalled", "truncated", "result_set_complete"):
        assert key in metadata, key


def test_the_sweep_sees_icite_as_an_envelope_now():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "tnt_env", ROOT / "scripts" / "test_new_tools.py"
    )
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)

    tools = json.loads((DATA / "icite_tools.json").read_text("utf-8"))
    tool = next(t for t in tools if t["name"] == "iCite_search_publications")

    assert runner.schema_describes_envelope(tool["return_schema"]) is True


def test_openfoodfacts_images_are_keyed_by_pattern():
    tools = json.loads((DATA / "openfoodfacts_tools.json").read_text("utf-8"))
    tool = next(t for t in tools if t["name"] == "OpenFoodFacts_get_product")
    images = tool["return_schema"]["oneOf"][0]["properties"]["product"][
        "properties"
    ]["images"]

    assert "properties" not in images
    assert "^[0-9]+$" in images["patternProperties"]
    # uploaded_t/imgid/rev arrive as a decimal string on some products and a
    # number on others; the enumerated schema recorded whichever the sampled
    # product sent, per image id.
    uploaded = images["patternProperties"]["^[0-9]+$"]["properties"]["uploaded_t"]
    assert {"string", "integer"} <= set(uploaded["type"])
