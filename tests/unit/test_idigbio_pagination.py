"""iDigBio tools: pagination, and the GBIF behaviours that answer wrongly in silence.

iDigBio's own search API was retired (HTTP 410 on every path), so these tools now
read the same holdings through GBIF's occurrence API restricted to GBIF's iDigBio
network. GBIF does not refuse a filter it does not understand -- it answers as if
the filter were absent -- so each place where that could turn a narrow question
into the whole 89-million-record network is pinned here.
"""

import ast
import json
from pathlib import Path

import pytest
from jsonschema import validate

from tooluniverse.idigbio_tool import (
    IDIGBIO_NETWORK_KEY,
    iDigBioRecordTool,
    iDigBioSearchTool,
)
import tooluniverse.idigbio_tool as idigbio_tool


ROOT = Path(__file__).parents[2]
CONFIGS = json.loads((ROOT / "src/tooluniverse/data/idigbio_tools.json").read_text())


def _config(name):
    return next(config for config in CONFIGS if config["name"] == name)


class _Response:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


COUNTRIES = [
    {
        "iso2": "US",
        "iso3": "USA",
        "title": "United States",
        "enumName": "UNITED_STATES",
    },
    {"iso2": "MX", "iso3": "MEX", "title": "Mexico", "enumName": "MEXICO"},
]

SEARCH_PAYLOAD = {
    "count": 23,
    "results": [
        {"key": 11, "scientificName": "Quercus fusiformis Small", "genus": "Quercus"},
        {"key": 12, "scientificName": "Quercus virginiana Mill.", "genus": "Quercus"},
    ],
}


def _fake_gbif(monkeypatch, *, match=None, search=SEARCH_PAYLOAD, occurrence=None):
    """Answer GBIF's four endpoints from fixtures, recording every call."""
    calls = []

    def fake_get(url, **kwargs):
        params = kwargs.get("params") or {}
        calls.append({"url": url, "params": dict(params)})
        if url.endswith("/enumeration/country"):
            return _Response(COUNTRIES)
        if url.endswith("/species/match"):
            rank = next(iter(params))
            value = params[rank]
            if match is not None:
                return _Response(match)
            return _Response(
                {
                    "usageKey": 2877951,
                    "canonicalName": value.capitalize(),
                    "rank": rank.upper(),
                    "matchType": "EXACT",
                    "familyKey": 4689,
                    "family": "Fagaceae",
                }
            )
        if url.endswith("/occurrence/search"):
            return _Response(search)
        return _Response(occurrence if occurrence is not None else {})

    monkeypatch.setattr(idigbio_tool.requests, "get", fake_get)
    # The country table is cached across calls; each test starts from empty.
    monkeypatch.setattr(idigbio_tool, "_countries_cache", None)
    return calls


def _occurrence_params(calls):
    return next(c["params"] for c in calls if c["url"].endswith("/occurrence/search"))


@pytest.mark.parametrize("name", ["iDigBio_search_records", "iDigBio_search_media"])
def test_search_forwards_offset_and_exposes_continuation(monkeypatch, name):
    calls = _fake_gbif(monkeypatch)
    out = iDigBioSearchTool(_config(name)).run(
        {"genus": "Quercus", "limit": 2, "offset": 5}
    )
    params = _occurrence_params(calls)
    assert params["limit"] == 2
    assert params["offset"] == 5
    assert params["networkKey"] == IDIGBIO_NETWORK_KEY
    assert out["metadata"]["total_available"] == 23
    assert out["metadata"]["total_available_is_exact"] is True
    assert out["metadata"]["returned"] == 2
    assert out["metadata"]["has_more"] is True
    assert out["metadata"]["next_offset"] == 7
    assert out["metadata"]["truncated"] is True
    assert out["metadata"]["result_set_complete"] is False
    assert out["metadata"]["query"] == {"genus": "Quercus"}
    assert out["metadata"]["network_key"] == IDIGBIO_NETWORK_KEY
    validate(out["data"], _config(name)["return_schema"])


@pytest.mark.parametrize(
    "arguments,parameter",
    [
        ({"genus": "Quercus", "limit": 0}, "limit"),
        ({"genus": "Quercus", "limit": 101}, "limit"),
        ({"genus": "Quercus", "limit": True}, "limit"),
        ({"genus": "Quercus", "limit": "3"}, "limit"),
        ({"genus": "Quercus", "offset": -1}, "offset"),
        ({"genus": "Quercus", "offset": True}, "offset"),
        ({"genus": "Quercus", "offset": "3"}, "offset"),
    ],
)
def test_invalid_pagination_fails_before_network(monkeypatch, arguments, parameter):
    monkeypatch.setattr(
        idigbio_tool.requests,
        "get",
        lambda *_args, **_kwargs: pytest.fail("network must not be called"),
    )
    out = iDigBioSearchTool(_config("iDigBio_search_records")).run(arguments)
    assert out["status"] == "error"
    assert out["parameter"] == parameter


@pytest.mark.parametrize(
    "name,expected",
    [
        ("iDigBio_search_records", [None] * 11 + [10, 0]),
        ("iDigBio_search_media", [None] * 11 + [10, 0]),
    ],
)
def test_generated_wrappers_match_pagination_defaults(name, expected):
    path = ROOT / "src/tooluniverse/tools" / f"{name}.py"
    function = next(
        node
        for node in ast.parse(path.read_text()).body
        if isinstance(node, ast.FunctionDef)
    )
    assert [ast.literal_eval(node) for node in function.args.defaults] == expected


# --- the four GBIF behaviours that would answer wrongly without a guard -------


@pytest.mark.parametrize("rank", ["phylum", "class", "order", "family", "genus"])
def test_a_higher_taxon_becomes_a_taxon_key_and_is_never_sent_as_itself(
    monkeypatch, rank
):
    """GBIF has no occurrence filter for these ranks and ignores them in silence.

    Measured against the live API: `genus=Panthera` returned 89,279,963 records,
    exactly the unfiltered network count. The name has to arrive as a taxonKey.
    """
    calls = _fake_gbif(monkeypatch)
    out = iDigBioSearchTool(_config("iDigBio_search_records")).run({rank: "Quercus"})
    params = _occurrence_params(calls)
    assert params["taxonKey"] == 2877951
    assert rank not in params
    assert out["metadata"]["taxa_resolved"][rank]["taxon_key"] == 2877951


def test_a_rank_match_that_climbed_to_a_higher_rank_is_refused(monkeypatch):
    """species/match answers an unmatchable name by climbing, not by failing.

    `species/match?name=Panthera&rank=GENUS` returns matchType=HIGHERRANK,
    rank=KINGDOM, usageKey=1 -- Animalia, 44,405,370 records. Filtering on that
    would answer a question about one genus with a whole kingdom.
    """
    calls = _fake_gbif(
        monkeypatch,
        match={
            "usageKey": 1,
            "scientificName": "Animalia",
            "rank": "KINGDOM",
            "matchType": "HIGHERRANK",
        },
    )
    out = iDigBioSearchTool(_config("iDigBio_search_records")).run(
        {"genus": "Panthera"}
    )
    assert out["status"] == "error"
    assert out["parameter"] == "genus"
    assert "HIGHERRANK" in out["error"]
    assert not [c for c in calls if c["url"].endswith("/occurrence/search")]


def test_a_name_gbif_cannot_place_is_refused(monkeypatch):
    _fake_gbif(monkeypatch, match={"matchType": "NONE"})
    out = iDigBioSearchTool(_config("iDigBio_search_records")).run({"genus": "Zzzz"})
    assert out["status"] == "error"
    assert out["parameter"] == "genus"


def test_two_ranks_no_taxon_satisfies_are_refused_not_narrowed(monkeypatch):
    """genus Quercus is not in family Felidae; the conjunction is empty.

    GBIF ORs repeated taxonKey values, so handing it both would widen the
    question instead of narrowing it, and using only the narrowest rank would
    drop the other filter without saying so.
    """
    calls = _fake_gbif(monkeypatch)
    out = iDigBioSearchTool(_config("iDigBio_search_records")).run(
        {"genus": "Quercus", "family": "Felidae"}
    )
    assert out["status"] == "error"
    assert out["parameter"] == "family"
    assert "Fagaceae" in out["error"]
    assert not [c for c in calls if c["url"].endswith("/occurrence/search")]


def test_a_country_name_is_resolved_to_the_iso_code_gbif_filters_on(monkeypatch):
    """ "United States", "USA" and "us" each returned count=0 against the live API.

    GBIF filters on the alpha-2 code and reports an unrecognised value as no
    records rather than as an error, so every spelling is resolved first.
    """
    for spelling in ("United States", "USA", "us", "US", "UNITED_STATES"):
        calls = _fake_gbif(monkeypatch)
        out = iDigBioSearchTool(_config("iDigBio_search_records")).run(
            {"country": spelling}
        )
        assert out["status"] == "success", spelling
        assert _occurrence_params(calls)["country"] == "US", spelling


def test_an_unrecognised_country_is_refused_rather_than_sent(monkeypatch):
    calls = _fake_gbif(monkeypatch)
    out = iDigBioSearchTool(_config("iDigBio_search_records")).run(
        {"country": "Narnia"}
    )
    assert out["status"] == "error"
    assert out["parameter"] == "country"
    assert not [c for c in calls if c["url"].endswith("/occurrence/search")]


def test_an_unknown_facet_is_refused_rather_than_returned_empty(monkeypatch):
    """GBIF answers a facet name it does not know with an empty facet list.

    Returned as-is that reads as "no records have this field", which is a
    different statement from "this field cannot be faceted on".
    """
    calls = _fake_gbif(monkeypatch, search={"count": 5, "facets": []})
    out = iDigBioSearchTool(_config("iDigBio_summary_facets")).run(
        {"genus": "Quercus", "top_fields": "notafacet"}
    )
    assert out["status"] == "error"
    assert out["parameter"] == "top_fields"
    assert not [c for c in calls if c["url"].endswith("/occurrence/search")]


def test_a_known_facet_is_asked_for_under_its_gbif_name_and_returned_under_ours(
    monkeypatch,
):
    calls = _fake_gbif(
        monkeypatch,
        search={
            "count": 5198,
            "facets": [
                {"field": "GENUS_KEY", "counts": [{"name": "2435098", "count": 5198}]}
            ],
        },
    )
    out = iDigBioSearchTool(_config("iDigBio_summary_facets")).run(
        {"country": "Mexico", "top_fields": "genus", "count": 3}
    )
    params = _occurrence_params(calls)
    assert params["facet"] == ["genusKey"]
    assert params["facetLimit"] == 3
    assert out["data"]["itemCount"] == 5198
    assert out["data"]["facets"] == {"genus": {"2435098": 5198}}
    validate(out["data"], _config("iDigBio_summary_facets")["return_schema"])


def test_the_retired_query_language_is_refused_with_what_to_use_instead(monkeypatch):
    calls = _fake_gbif(monkeypatch)
    out = iDigBioSearchTool(_config("iDigBio_search_records")).run(
        {"rq": '{"genus": "Quercus"}'}
    )
    assert out["status"] == "error"
    assert out["parameter"] == "rq"
    assert "scientificname" in out["error"]
    assert calls == []


# --- the identifier space that went away with the old API ---------------------


def test_a_legacy_idigbio_uuid_is_refused_with_how_to_find_the_record(monkeypatch):
    calls = _fake_gbif(monkeypatch)
    out = iDigBioRecordTool(_config("iDigBio_get_record")).run(
        {"occurrence_key": "b659bd7f-7fa7-434b-80e7-2be10d1c4e80"}
    )
    assert out["status"] == "error"
    assert out["parameter"] == "occurrence_key"
    # Not just "this is not a GBIF key" -- the message has to name what became of
    # those ids, or the refusal reads as a validation quibble.
    assert "legacy iDigBio record UUID" in out["error"]
    assert "retired" in out["error"]
    assert "iDigBio_search_records" in out["error"]
    assert calls == []


def test_a_gbif_occurrence_key_is_fetched_and_network_membership_reported(monkeypatch):
    _fake_gbif(
        monkeypatch,
        occurrence={
            "key": 6158969750,
            "scientificName": "Quercus fusiformis Small",
            "networkKeys": [IDIGBIO_NETWORK_KEY, "other"],
        },
    )
    out = iDigBioRecordTool(_config("iDigBio_get_record")).run(
        {"occurrence_key": "6158969750"}
    )
    assert out["status"] == "success"
    assert out["data"]["gbif_id"] == 6158969750
    assert out["metadata"]["in_idigbio_network"] is True
    assert out["data"]["data"]["scientificName"] == "Quercus fusiformis Small"
    validate(out["data"], _config("iDigBio_get_record")["return_schema"])


def test_nothing_still_calls_the_retired_idigbio_api():
    """The legacy host answers 410 on every path, so no URL may still point at it.

    The host name itself is allowed to appear in prose -- several descriptions
    explain that those ids and that query language went away with it. What must
    not come back is a request built against it.
    """
    offenders = []
    for folder in ("src", "tests", "docs", "examples", "scripts"):
        for path in sorted((ROOT / folder).rglob("*")):
            if not path.is_file() or path.suffix not in {
                ".py",
                ".json",
                ".rst",
                ".md",
                ".txt",
            }:
                continue
            relative = path.relative_to(ROOT).as_posix()
            if relative == "tests/unit/test_idigbio_pagination.py":
                continue
            try:
                text = path.read_text(errors="ignore")
            except OSError:  # pragma: no cover - unreadable file
                continue
            if "https://search.idigbio.org" in text:
                offenders.append(relative)
    assert offenders == [], (
        "these still name the retired iDigBio search API: " + ", ".join(offenders)
    )


@pytest.mark.parametrize("asked", sorted(idigbio_tool._FACET_FIELDS))
def test_every_allowed_facet_matches_the_name_gbif_echoes_back(monkeypatch, asked):
    """GBIF echoes "genusKey" as "GENUS_KEY"; a mismatch would read as no data.

    The counts are matched back to the name the caller asked for by normalising
    that echo. If the normalisation missed a name the breakdown would come back
    empty, and an empty breakdown is what GBIF also returns for a facet it does
    not know -- so the failure would look like an answer.
    """
    gbif_name = idigbio_tool._FACET_FIELDS[asked]
    echoed = "".join("_" + c.lower() if c.isupper() else c for c in gbif_name).upper()
    _fake_gbif(
        monkeypatch,
        search={
            "count": 7,
            "facets": [{"field": echoed, "counts": [{"name": "v", "count": 7}]}],
        },
    )
    out = iDigBioSearchTool(_config("iDigBio_summary_facets")).run(
        {"scientificname": "Puma concolor", "top_fields": asked}
    )
    assert out["status"] == "success"
    assert out["data"]["facets"] == {asked: {"v": 7}}, (
        f"{asked} -> {gbif_name}: GBIF's echo {echoed!r} did not match back, so "
        "the breakdown came back empty"
    )
