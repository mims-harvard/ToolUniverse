"""return_schema declarations that rejected the tool's own live output.

Found by validating every keyless tool's first example against its schema (the check
``tu test`` performs): ComplexPortal_get_complex declared complex_id/name/species/
taxonomy_id/description as ``null`` (written from an all-null response), OncoKB declared
``query.canonicalTranscript`` as ``null``, MyChem declared ``pubchem`` as an object
although some hits carry a list, and WorldBank_search_indicators' metadata ``source``
string collided with the schema's ``source`` object.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import jsonschema
import pytest

from tooluniverse import worldbank_tool
from tooluniverse.complex_portal_tool import ComplexPortalTool
from tooluniverse.worldbank_tool import WorldBankIndicatorSearchTool

pytestmark = pytest.mark.unit

DATA = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data"


def _config(filename, name):
    tools = json.loads((DATA / filename).read_text(encoding="utf-8"))
    return next(t for t in tools if t["name"] == name)


def test_complex_portal_output_validates_against_its_schema():
    record = {
        "complexAc": "CPX-100",
        "name": "Cathepsin-B - cystatin-A complex",
        "systematicName": "Ctsb:Csta",
        "species": "Mus musculus; 10090",
        "functions": ["Complex of cathepsin-B with cystatin-A."],
        "complexAssemblies": ["Heterodimer"],
        "predictedComplex": False,
        "participants": [],
        "crossReferences": [],
    }
    response = MagicMock()
    response.json.return_value = record
    config = _config("complex_portal_tools.json", "ComplexPortal_get_complex")
    with patch("tooluniverse.complex_portal_tool.requests.get", return_value=response):
        result = ComplexPortalTool(config).run({"complex_id": "CPX-100"})
    assert result["status"] == "success"
    jsonschema.validate(result["data"], config["return_schema"])


def test_world_bank_search_output_validates_against_its_schema():
    catalog = [
        {
            "id": "NY.GDP.MKTP.CD",
            "name": "GDP (current US$)",
            "unit": "",
            "source": {"id": "2", "value": "World Development Indicators"},
            "sourceNote": "GDP at purchaser's prices",
            "topics": [{"id": "3", "value": "Economy & Growth"}],
        }
    ]
    config = _config("worldbank_tools.json", "WorldBank_search_indicators")
    tool = WorldBankIndicatorSearchTool(config)
    with patch.object(worldbank_tool, "_catalog", catalog):
        result = tool.run({"query": "GDP"})
    assert result["status"] == "success"
    jsonschema.validate(result["data"], config["return_schema"])


@pytest.mark.parametrize(
    "name", ["OncoKB_annotate_variant", "OncoKB_annotate_mutations"]
)
def test_oncokb_schema_allows_a_canonical_transcript_string(name):
    schema = _config("oncokb_tools.json", name)["return_schema"]
    query = schema["oneOf"][0]["properties"]["query"]["properties"][
        "canonicalTranscript"
    ]
    types = query["type"] if isinstance(query["type"], list) else [query["type"]]
    assert "string" in types


def test_mychem_schema_allows_pubchem_as_a_list():
    schema = _config("biothings_tools.json", "MyChem_query_chemicals")["return_schema"]
    pubchem = schema["properties"]["hits"]["items"]["properties"]["pubchem"]
    payload = {
        "took": 1,
        "total": 1,
        "hits": [{"_id": "x", "pubchem": [{"cid": 1}, {"cid": 2}]}],
    }
    jsonschema.validate(payload, schema)
    assert "array" in pubchem["type"]
