"""WoRMS_search_species must disclose (and let callers lift) the marine filter.

WoRMS's AphiaRecordsByName endpoint defaults to ``marine_only=true``. The tool
neither set nor exposed that parameter, so a search for a real, WoRMS-catalogued
but non-marine taxon came back as a confident empty success:

    WoRMS_search_species {"query": "Schistosoma mansoni"}
    -> {"status": "success", "data": [], "count": 0,
        "message": "No results found for this query"}

even though AphiaID 1599676 exists and the sibling tools (WoRMS_get_classification,
WoRMS_get_distribution) serve it happily -- their docs say to obtain the AphiaID
from WoRMS_search_species, so the documented workflow was unreachable for every
freshwater/terrestrial taxon.

The fix is additive: a new optional ``marine_only`` parameter that defaults to
today's behaviour, plus a zero-result message that names the filter. Callers who
do not pass it must see byte-identical requests and identical result sets.
"""

from unittest.mock import MagicMock, patch

from tooluniverse.worms_tool import WoRMSRESTTool


SEARCH_CONFIG = {
    "type": "WoRMSRESTTool",
    "name": "WoRMS_search_species",
    "description": "Search species in WoRMS",
    "parameter": {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "limit": {"type": "integer"},
            "offset": {"type": "integer"},
            "marine_only": {"type": "boolean"},
        },
        "required": ["query"],
    },
    "fields": {"return_format": "JSON"},
}

# Trimmed from the real upstream response for
# AphiaRecordsByName/Schistosoma%20mansoni?marine_only=false&offset=1
SCHISTOSOMA = {
    "AphiaID": 1599676,
    "scientificname": "Schistosoma mansoni",
    "authority": "Sambon, 1907",
    "status": "accepted",
    "rank": "Species",
    "valid_AphiaID": 1599676,
    "kingdom": "Animalia",
    "phylum": "Platyhelminthes",
    "class": "Trematoda",
    "family": "Schistosomatidae",
    "isMarine": None,
    "isFreshwater": 1,
    "isTerrestrial": 1,
    "match_type": "exact",
}

GADUS = {
    "AphiaID": 126436,
    "scientificname": "Gadus morhua",
    "status": "accepted",
    "isMarine": 1,
    "match_type": "exact",
}


def _session(records):
    """Session returning `records` on the first page, then nothing."""

    def get(url, timeout=None):
        response = MagicMock()
        offset = int(url.split("offset=")[1].split("&")[0]) if "offset=" in url else 1
        page = records if offset == 1 else []
        if not page:
            response.status_code = 204
            response.text = ""
            response.json.return_value = []
            return response
        response.status_code = 200
        response.text = "[...]"
        response.json.return_value = page
        return response

    session = MagicMock()
    session.get.side_effect = get
    return session


def _run(arguments, records):
    tool = WoRMSRESTTool(dict(SEARCH_CONFIG))
    tool.session = _session(records)
    result = tool.run(arguments)
    return result, [c.args[0] for c in tool.session.get.call_args_list]


# --- (a) marine_only unset: request unchanged, empty answer now discloses -----


def test_unset_marine_only_sends_todays_request_unchanged():
    """No marine_only argument => no marine_only in the outgoing URL."""
    _, urls = _run({"query": "Schistosoma mansoni"}, [])
    assert urls, "the tool must actually call WoRMS"
    for url in urls:
        assert "marine_only" not in url
        assert url.endswith("?offset=1")


def test_empty_result_discloses_the_marine_filter():
    """A confidently-wrong empty answer becomes an actionable one."""
    result, _ = _run({"query": "Schistosoma mansoni"}, [])
    assert result["status"] == "success"
    assert result["data"] == []
    assert result["count"] == 0
    message = result["message"].lower()
    assert "marine" in message, message
    # It must name the escape hatch, not merely mention the restriction.
    assert "marine_only=false" in message, message
    assert "freshwater" in message and "terrestrial" in message, message


def test_empty_result_reports_the_effective_marine_only_value():
    result, _ = _run({"query": "Schistosoma mansoni"}, [])
    assert result["marine_only"] is True


# --- (b) marine_only=false is forwarded and its records parse normally --------


def test_marine_only_false_is_forwarded_upstream():
    _, urls = _run(
        {"query": "Schistosoma mansoni", "marine_only": False}, [SCHISTOSOMA]
    )
    assert urls
    assert all("marine_only=false" in url for url in urls), urls
    # Still 1-based offset paging, unchanged.
    assert "offset=1" in urls[0]


def test_marine_only_false_returns_the_non_marine_record():
    result, _ = _run(
        {"query": "Schistosoma mansoni", "marine_only": False}, [SCHISTOSOMA]
    )
    assert result["status"] == "success"
    assert result["count"] == 1
    assert result["has_more"] is False
    assert result["marine_only"] is False
    record = result["data"][0]
    assert record["AphiaID"] == 1599676
    assert record["scientificname"] == "Schistosoma mansoni"
    # The AphiaID the sibling tools need is now reachable from the search.
    assert record["family"] == "Schistosomatidae"


def test_marine_only_true_is_forwarded_explicitly_when_requested():
    _, urls = _run({"query": "Gadus morhua", "marine_only": True}, [GADUS])
    assert all("marine_only=true" in url for url in urls), urls


def test_marine_only_accepts_json_string_booleans():
    """CLI/agent callers sometimes stringify booleans."""
    result, urls = _run(
        {"query": "Schistosoma mansoni", "marine_only": "false"}, [SCHISTOSOMA]
    )
    assert result["status"] == "success"
    assert result["marine_only"] is False
    assert all("marine_only=false" in url for url in urls)


def test_non_boolean_marine_only_is_rejected_clearly():
    result, _ = _run({"query": "Gadus", "marine_only": "maybe"}, [GADUS])
    assert result["status"] == "error"
    assert "marine_only" in result["error"]


# --- (c) a successful marine search is unchanged -----------------------------


def test_successful_marine_search_is_unchanged():
    result, urls = _run({"query": "Gadus morhua"}, [GADUS])
    assert result["status"] == "success"
    assert result["count"] == 1
    assert result["data"] == [GADUS]
    assert result["offset"] == 1
    assert result["limit"] == 20
    assert result["has_more"] is False
    # No behaviour change for the existing marine caller: same URL as before.
    assert urls[0].endswith("?offset=1")
    assert "marine_only" not in urls[0]
    # A non-empty result carries no filter warning.
    assert "message" not in result


def test_marine_only_does_not_leak_into_aphia_operations():
    """Enrichment endpoints keep their exact URLs."""
    config = dict(SEARCH_CONFIG)
    config["fields"] = {"operation": "classification"}
    tool = WoRMSRESTTool(config)
    response = MagicMock()
    response.status_code = 200
    response.text = "{}"
    response.json.return_value = {"AphiaID": 1599676, "rank": "Species"}
    session = MagicMock()
    session.get.return_value = response
    tool.session = session
    result = tool.run({"AphiaID": 1599676, "marine_only": False})
    assert result["status"] == "success"
    assert "marine_only" not in session.get.call_args.args[0]


# --- shipped config documents the new parameter ------------------------------


def _search_config():
    import json
    from pathlib import Path

    path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "tooluniverse"
        / "data"
        / "worms_tools.json"
    )
    return {t["name"]: t for t in json.loads(path.read_text())}


def test_config_declares_marine_only_and_documents_the_default():
    tools = _search_config()
    search = tools["WoRMS_search_species"]
    param = search["parameter"]["properties"]["marine_only"]
    assert param["type"] == "boolean"
    assert param["default"] is True
    assert "marine_only" not in search["parameter"].get("required", [])
    assert "marine" in search["description"].lower()
    assert "marine_only=false" in search["description"]


def test_sibling_tools_point_at_the_new_parameter():
    """Their docs send callers to the search tool, which needed the caveat."""
    tools = _search_config()
    for name in (
        "WoRMS_get_classification",
        "WoRMS_get_distribution",
        "WoRMS_get_vernaculars",
        "WoRMS_get_synonyms",
    ):
        text = tools[name]["parameter"]["properties"]["AphiaID"]["description"]
        assert "WoRMS_search_species" in text
        assert "marine_only=false" in text, name


def test_return_schema_does_not_forbid_extra_metadata():
    """The `marine_only` echo must not violate the declared schema."""
    search = _search_config()["WoRMS_search_species"]
    assert "additionalProperties" not in str(search["return_schema"])


@patch("tooluniverse.worms_tool.requests")
def test_no_network_is_touched(_requests):
    """Guard: the module's requests object is never used directly here."""
    result, _ = _run({"query": "Schistosoma mansoni"}, [])
    assert result["status"] == "success"
