"""Parameters that are optional or defaulted must not be listed as required.

Found by scanning every schema for required parameters whose description says
"optional" or that carry a default, then confirming against the tool code/behavior:

* DBpedia_SPARQL_query: max_results is an optional limit override (the query's own
  LIMIT applies), but a call without it was rejected.
* HPA_get_disease_expression_by_gene_tissue_disease: tissue_type is optional (the
  code reports "Not specified").
* OpenML_search_datasets: limit is a URL path segment, so it can only be omitted if
  the schema supplies a real default; the description said "default 20" in prose only.
"""

import json
from pathlib import Path

import jsonschema
import pytest

pytestmark = pytest.mark.unit

_DATA = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data"


def _tool(filename, name):
    for tool in json.loads((_DATA / filename).read_text()):
        if tool["name"] == name:
            return tool
    raise AssertionError(name)


def test_dbpedia_max_results_is_optional():
    schema = _tool("dbpedia_tools.json", "DBpedia_SPARQL_query")["parameter"]
    jsonschema.validate({"sparql": "SELECT ?s WHERE {?s ?p ?o} LIMIT 1"}, schema)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({}, schema)


def test_hpa_tissue_type_is_optional():
    schema = _tool(
        "hpa_tools.json", "HPA_get_disease_expression_by_gene_tissue_disease"
    )["parameter"]
    jsonschema.validate({"gene_name": "TP53", "disease_name": "breast cancer"}, schema)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"gene_name": "TP53"}, schema)


def test_openml_limit_is_optional_and_has_a_real_default_for_its_path_segment():
    tool = _tool("openml_tools.json", "OpenML_search_datasets")
    assert "{limit}" in tool["fields"]["endpoint"]
    assert tool["parameter"].get("required", []) == []
    assert tool["parameter"]["properties"]["limit"]["default"] == 20
