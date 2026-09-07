"""A ChEMBL filter ChEMBL does not apply must not come back as a success.

ChEMBLRESTTool sent every leftover argument to ChEMBL as a query parameter.
ChEMBL ignores parameters it does not recognise and answers with the whole
resource, so a misspelled or unsupported filter came back as ``status: success``
over a table answering a different question. Verified live against /target.json:

    (no filter)                      total_count 18552, first row Homo sapiens
    ?species=Schistosoma+mansoni     total_count 18552, first row Homo sapiens
    ?bananaparam=x                   total_count 18552, first row Homo sapiens
    ?organism=Schistosoma+mansoni    total_count 12,    first row S. mansoni

``organism`` is the real filter; ``species`` is not, and the caller was told
18552 targets matched their species restriction.

The check consults ChEMBL's own published filter list
(/<resource>/schema.json, key "filtering") rather than the tool config, because
the two disagree in both directions and each direction was a live defect:

  * ``assay_organism`` is a real /assay.json filter that ChEMBL_search_assays
    does not declare -- it returns 591 genuine L. major assays, and a
    config-only check rejected it.
  * ``organism__icontains`` looks like ChEMBL filter syntax, but ``organism`` is
    not an /assay.json field, so ChEMBL drops it exactly like ``bananaparam``
    and returns all 1,970,438 assays. Trusting the ``__`` suffix would have let
    the defect back in through the escape hatch.

Three tools shipped test_examples that were themselves instances of this, each
confirmed against the live API by comparing filtered and unfiltered responses:

    /binding_site.json?target_chembl_id__exact=CHEMBL2074  -> same row as no filter
    /protein_classification.json?target_chembl_id__exact=. -> total_count 905 either way
    /activity.json?compound_record_id__exact=1             -> activity_id 31863, as unfiltered
    /activity.json?record_id=1                             -> activity_id 57025
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse import chem_tool
from tooluniverse.chem_tool import ChEMBLRESTTool

pytestmark = pytest.mark.unit

CONFIG = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "tooluniverse"
    / "data"
    / "chembl_tools.json"
)

# Verbatim from https://www.ebi.ac.uk/chembl/api/data/<resource>/schema.json,
# key "filtering". Trimmed to the fields these tests exercise.
UPSTREAM_FILTERS = {
    "target": ["organism", "pref_name", "target_chembl_id", "target_type", "tax_id"],
    "assay": ["assay_chembl_id", "assay_organism", "assay_type", "target_chembl_id"],
    "binding_site": ["site_components", "site_id", "site_name"],
    "protein_classification": ["protein_class_id", "pref_name", "class_level"],
    "activity": ["activity_id", "record_id", "target_chembl_id", "molecule_chembl_id"],
}


def _configs():
    with open(CONFIG) as fh:
        return json.load(fh)


def _tool(name):
    for cfg in _configs():
        if cfg["name"] == name:
            return ChEMBLRESTTool(cfg)
    raise AssertionError(f"{name} not in chembl_tools.json")


@pytest.fixture(autouse=True)
def _isolated_schema_cache():
    """Serve ChEMBL's filter lists from the fixture; never touch the network."""
    chem_tool._CHEMBL_FILTER_FIELDS.clear()
    chem_tool._CHEMBL_FILTER_FIELDS.update(
        {resource: set(fields) for resource, fields in UPSTREAM_FILTERS.items()}
    )
    yield
    chem_tool._CHEMBL_FILTER_FIELDS.clear()


def _patched_request():
    response = MagicMock()
    response.status_code = 200
    response.url = "https://www.ebi.ac.uk/chembl/api/data/target.json"
    response.json.return_value = {
        "targets": [],
        "assays": [],
        "binding_sites": [],
        "protein_classifications": [],
        "activities": [],
        "page_meta": {"total_count": 0},
    }
    response.raise_for_status.return_value = None
    return patch("tooluniverse.chem_tool.request_with_retry", return_value=response)


def test_invented_filter_is_rejected_and_never_reaches_chembl():
    """`species` must error, and must not be sent as an ignored query param."""
    with _patched_request() as request:
        result = _tool("ChEMBL_search_targets").run(
            {"species": "Schistosoma mansoni", "limit": 3}
        )
    assert result["status"] == "error"
    assert "species" in result["error"]
    # Unusable unless it names the filter that does work.
    assert "organism" in result["error"]
    # Nothing was sent: the point is that ChEMBL would have answered 200 OK.
    assert request.call_count == 0


def test_lookup_suffix_on_a_field_the_resource_lacks_is_rejected():
    """`organism__icontains` is not filter syntax on /assay.json -- it is noise."""
    with _patched_request() as request:
        result = _tool("ChEMBL_search_assays").run(
            {"organism__icontains": "Leishmania major", "limit": 2}
        )
    assert result["status"] == "error"
    assert "organism__icontains" in result["error"]
    assert "assay_organism" in result["error"]
    assert request.call_count == 0


def test_real_upstream_filter_absent_from_the_config_still_works():
    """`assay_organism` filters /assay.json but ChEMBL_search_assays omits it."""
    declared = _tool("ChEMBL_search_assays").tool_config["parameter"]["properties"]
    assert "assay_organism" not in declared
    with _patched_request() as request:
        result = _tool("ChEMBL_search_assays").run(
            {"assay_organism": "Leishmania major", "limit": 2}
        )
    assert result["status"] == "success"
    assert request.call_args.kwargs["params"]["assay_organism"] == "Leishmania major"


def test_lookup_suffix_on_a_real_field_is_passed_through():
    with _patched_request() as request:
        result = _tool("ChEMBL_search_assays").run(
            {"assay_organism__icontains": "leishmania", "limit": 2}
        )
    assert result["status"] == "success"
    sent = request.call_args.kwargs["params"]
    assert sent["assay_organism__icontains"] == "leishmania"


def test_declared_filter_still_reaches_chembl_on_the_wire():
    """Control: `organism` is both declared and a real /target.json filter."""
    with _patched_request() as request:
        result = _tool("ChEMBL_search_targets").run(
            {"organism": "Schistosoma mansoni", "limit": 3}
        )
    assert result["status"] == "success"
    assert request.call_args.kwargs["params"]["organism"] == "Schistosoma mansoni"


def test_rewritten_parameter_is_checked_after_rewriting():
    """`target_chembl_id` becomes `target_chembl_id__exact`, inert on /binding_site.

    Checking the caller's arguments instead of the built query would miss this:
    the argument name looks plausible and only the rewritten form is sent.
    """
    with _patched_request() as request:
        result = _tool("ChEMBL_search_binding_sites").run(
            {"target_chembl_id": "CHEMBL2074", "limit": 2}
        )
    assert result["status"] == "error"
    assert "target_chembl_id__exact" in result["error"]
    assert "site_name" in result["error"]
    assert request.call_count == 0


def test_compound_record_id_is_sent_as_the_column_activity_actually_has():
    """The tool's own required parameter returned the whole activity table."""
    with _patched_request() as request:
        result = _tool("ChEMBL_get_compound_record_activities").run(
            {"compound_record_id__exact": "1", "limit": 2}
        )
    assert result["status"] == "success"
    sent = request.call_args.kwargs["params"]
    assert sent["record_id"] == "1"
    assert "compound_record_id__exact" not in sent


def test_path_placeholder_is_not_treated_as_a_filter():
    """`smiles`/`threshold` select the resource in the path, not via filtering."""
    tool = _tool("ChEMBL_search_similarity")
    args = {"smiles": "CC(=O)Oc1ccccc1C(=O)O", "threshold": 70, "limit": 2}
    url = tool._build_url(args)
    chem_tool._CHEMBL_FILTER_FIELDS["similarity"] = {"molecule_chembl_id", "pref_name"}
    assert tool._inert_filters(tool._build_params(args), url) == []


def test_unavailable_upstream_list_reports_nothing():
    """A failed schema fetch must not turn working queries into errors."""
    chem_tool._CHEMBL_FILTER_FIELDS.clear()
    with patch(
        "tooluniverse.chem_tool.request_with_retry",
        side_effect=OSError("no network"),
    ):
        tool = _tool("ChEMBL_search_targets")
        params = {"species": "Schistosoma mansoni", "limit": 3}
        url = "https://www.ebi.ac.uk/chembl/api/data/target.json"
        assert tool._inert_filters(params, url) == []
        # Cached as unavailable, so the failing fetch is not repeated per call.
        assert chem_tool._CHEMBL_FILTER_FIELDS["target"] is None


def test_no_shipped_test_example_uses_a_filter_known_to_be_inert():
    """The three corrected examples must not come back.

    Hermetic: names the exact query parameters proven inert against the live
    API, rather than re-deriving them, so it bites without a network call.
    """
    known_inert = {
        "binding_site": {"target_chembl_id__exact"},
        "protein_classification": {"target_chembl_id__exact"},
        "activity": {"compound_record_id__exact", "compound_record_id"},
    }
    offenders = []
    for cfg in _configs():
        if cfg.get("type") != "ChEMBLRESTTool":
            continue
        tool = ChEMBLRESTTool(cfg)
        for example in cfg.get("test_examples", []):
            url = tool._build_url(example)
            resource = tool._resource_name(url)
            sent = set(tool._build_params(example))
            bad = sent & known_inert.get(resource, set())
            if bad:
                offenders.append((cfg["name"], example, sorted(bad)))
    assert offenders == []


def test_no_declared_parameter_is_a_filter_known_to_be_inert():
    """Every parameter a tool advertises must be one ChEMBL will act on.

    A test_example sweep alone misses this: `ChEMBL_search_documents.document_id`
    and `ChEMBL_search_compound_structural_alerts.alert_name__contains` were
    declared but exercised by no example, and both returned their whole table
    (/document.json?document_id=1 is byte-identical to no filter;
    ?alert_name__contains=amine returns alert_id 1 like the unfiltered call).
    Under the new guard they would have become hard errors on a documented
    parameter -- worse for the caller than the silent version.
    """
    known_inert = {
        "binding_site": {"target_chembl_id__exact"},
        "protein_classification": {"target_chembl_id__exact"},
        "activity": {"compound_record_id__exact", "compound_record_id"},
        "document": {"document_id"},
        "compound_structural_alert": {"alert_name__contains"},
    }
    offenders = []
    for cfg in _configs():
        if cfg.get("type") != "ChEMBLRESTTool":
            continue
        tool = ChEMBLRESTTool(cfg)
        for name, spec in cfg.get("parameter", {}).get("properties", {}).items():
            sample = {name: 1 if spec.get("type") in ("integer", "number") else "x"}
            url = tool._build_url(sample)
            resource = tool._resource_name(url)
            sent = set(tool._build_params(sample))
            bad = sent & known_inert.get(resource, set())
            if bad:
                offenders.append((cfg["name"], name, sorted(bad)))
    assert offenders == []


@pytest.mark.network
def test_nothing_the_tools_advertise_builds_an_inert_query_live():
    """Sweep every test_example and every declared parameter against ChEMBL.

    Checked against the live filter lists, since a local copy would make this
    pass by construction. Three examples and two declared parameters failed it
    before this change.
    """
    chem_tool._CHEMBL_FILTER_FIELDS.clear()
    inert = []
    for cfg in _configs():
        if cfg.get("type") != "ChEMBLRESTTool":
            continue
        tool = ChEMBLRESTTool(cfg)
        probes = list(cfg.get("test_examples", []))
        for name, spec in cfg.get("parameter", {}).get("properties", {}).items():
            probes.append(
                {name: 1 if spec.get("type") in ("integer", "number") else "x"}
            )
        for probe in probes:
            url = tool._build_url(probe)
            bad = tool._inert_filters(tool._build_params(probe), url)
            if bad:
                inert.append((cfg["name"], probe, bad))
    assert inert == []
