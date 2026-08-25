"""A page size hard-coded in an endpoint template truncates the whole answer.

Three tools baked a row cap into their endpoint URL string. Because the cap
lives in the template rather than in a parameter, nothing in the response says
a cap was applied, and in two of the three the tool's own schema advertised a
`limit`/`rows` knob that could not reach it.

``CPIC_list_drugs`` -- endpoint ended ``&limit=200`` against a table of 324
drugs (``Content-Range: 0-323/324``), so it returned 200 and reported
``count: 200``. Measured live 2026-08-13, the 124 it dropped included
**codeine** and **abacavir**, both of which the tool's own description named as
covered, plus efavirenz, clozapine and voriconazole. A round-54 persona
concluded from this tool that efavirenz has no CPIC guidance; it has a
guideline. Undeclared ``limit``/``offset`` were accepted and did change the
result (``{"limit": 5}`` -> 5 rows), while the echoed ``url`` always read
``limit=200`` -- a published URL that did not describe the request made.
PostgREST returns the whole table when no limit is sent, so removing the cap
is the fix; ``limit``/``offset`` are now declared, and ``echo_request_url``
makes the echoed URL the one requests actually sent.

``GO_get_annotations_for_gene`` -- endpoint ended ``&rows=50`` with no
``{rows}`` placeholder, so the ``rows`` parameter its schema declared (default
documented as 100) was inert: ``rows=5`` and ``rows=300`` both returned 50.
TP53 matches 1812 annotation rows upstream, so the caller got 50 of 1812 and
could not ask for more. Substituting ``{rows}`` makes the declared default of
100 real and the parameter effective (verified live: 5 -> 5, 300 -> 300).

The remaining hard-coded cap, ``GO_search_terms``' ``rows=10``, is left alone
on purpose: that tool returns the raw Solr envelope, so its ``response.numFound``
is visible to the caller and the truncation is not silent.

Config-only assertions -- no network.
"""

import json
import re
from pathlib import Path

import pytest

import tooluniverse

pytestmark = pytest.mark.unit

DATA_DIR = Path(tooluniverse.__file__).parent / "data"


def _config(filename, tool_name):
    configs = json.loads((DATA_DIR / filename).read_text())
    return next(config for config in configs if config["name"] == tool_name)


def test_cpic_list_drugs_no_longer_caps_the_drug_table():
    fields = _config("cpic_tools.json", "CPIC_list_drugs")["fields"]

    assert "limit" not in fields["endpoint"]
    assert (
        fields["endpoint"] == "https://api.cpicpgx.org/v1/drug?select=name,guidelineid"
    )


def test_cpic_list_drugs_publishes_the_url_it_actually_requested():
    """Without this, `{"limit": 5}` returned 5 rows under a url saying limit=200."""
    fields = _config("cpic_tools.json", "CPIC_list_drugs")["fields"]

    assert fields["echo_request_url"] is True


def test_cpic_list_drugs_declares_the_paging_parameters_it_honours():
    """They were always forwarded to PostgREST; they were just undocumented."""
    properties = _config("cpic_tools.json", "CPIC_list_drugs")["parameter"][
        "properties"
    ]

    assert set(properties) == {"limit", "offset"}
    # No defaults: a default would be sent on every call and re-truncate the list.
    assert "default" not in properties["limit"]
    assert "default" not in properties["offset"]


def test_cpic_list_drugs_description_no_longer_claims_drugs_it_omitted():
    description = _config("cpic_tools.json", "CPIC_list_drugs")["description"]

    assert "324" in description
    for drug in ("codeine", "abacavir", "efavirenz", "clozapine"):
        assert drug in description


def test_go_annotations_rows_parameter_can_actually_reach_the_query():
    config = _config("gene_ontology_tools.json", "GO_get_annotations_for_gene")

    assert "{rows}" in config["fields"]["endpoint"]
    assert "rows=50" not in config["fields"]["endpoint"]
    assert config["parameter"]["properties"]["rows"]["default"] == 100


def test_go_annotations_description_admits_it_returns_a_page():
    description = _config("gene_ontology_tools.json", "GO_get_annotations_for_gene")[
        "description"
    ]

    assert "1812" in description
    assert "PAGE" in description


def test_no_gene_ontology_tool_declares_a_parameter_its_endpoint_cannot_use():
    """The class invariant behind the `rows=50` defect, guarded generically.

    `GeneOntologyTool._build_url` does placeholder substitution only -- it never
    forwards an argument as a query param -- so a declared parameter with no
    `{placeholder}` in the template is provably inert, whatever its description
    promises. Before this change `GO_get_annotations_for_gene` was the one tool
    that violated it.
    """
    inert = []
    for config in json.loads((DATA_DIR / "gene_ontology_tools.json").read_text()):
        endpoint = config["fields"]["endpoint"]
        if "?" not in endpoint:
            continue  # Biolink template path does forward params
        for name in config["parameter"]["properties"]:
            if f"{{{name}}}" not in endpoint:
                inert.append(f"{config['name']}.{name}")

    assert not inert, f"declared but unreachable: {inert}"


def test_no_endpoint_hardcodes_a_paging_value_its_own_schema_declares():
    """A hard-coded cap plus a declared knob sends the key twice.

    `BaseRESTTool._build_params` forwards any non-placeholder argument, so
    `CPIC_list_drugs` literally requested `limit=200&limit=5` and PostgREST
    honoured the last one while the echoed url advertised the first.
    """
    paging = re.compile(
        r"[?&](limit|offset|skip|per_page|page_size|pageSize|rows|size|retmax)=(\d+)",
        re.IGNORECASE,
    )
    offenders = []
    for path in DATA_DIR.rglob("*.json"):
        if "broken_apis" in path.parts:
            continue
        try:
            configs = json.loads(path.read_text())
        except (ValueError, UnicodeDecodeError):
            continue
        if not isinstance(configs, list):
            continue
        for config in configs:
            if not isinstance(config, dict) or not isinstance(
                config.get("fields"), dict
            ):
                continue
            endpoint = config["fields"].get("endpoint")
            if not isinstance(endpoint, str):
                continue
            declared = config.get("parameter", {}).get("properties", {}) or {}
            for match in paging.finditer(endpoint):
                if match.group(1) in declared:
                    offenders.append(f"{config['name']}: {match.group(0)}")

    assert not offenders, f"hard-coded page size shadows a declared param: {offenders}"


def test_go_search_terms_keeps_its_cap_because_it_reports_num_found():
    """The negative control: this endpoint's cap is disclosed, so it stays."""
    config = _config("gene_ontology_tools.json", "GO_search_terms")

    assert "rows=10" in config["fields"]["endpoint"]
    assert "extract_path" not in config["fields"]
    assert "numFound" in json.dumps(config["return_schema"])
