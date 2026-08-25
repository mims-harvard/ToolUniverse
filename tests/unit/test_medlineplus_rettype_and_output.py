"""Regression guards for MedlinePlus_search_topics_by_keyword.

Three separate defects, all confirmed live against NLM's wsearch service:

1. Only rettype="topic" parsed. wsearch returns the health-topic data in two
   different shapes: rettype=topic ships a single <content name="healthTopic">
   node wrapping a structured <health-topic> record, while rettype=brief ships
   several flat <content name="title|altTitle|FullSummary|groupName|snippet">
   nodes (and rettype=all ships both in one list). The parser only handled
   `doc["content"]` when xmltodict gave it a *dict* -- the brief/all list shape
   fell straight through, so a perfectly good HTTP 200 with 2 documents was
   discarded with "Failed to parse health topic information".

2. Developer debug output. Every call print()ed the request URL, response
   status/length, the first 500 response characters, the parse strategy, the
   top-level keys and a 2000-character dump of the raw structure to stdout,
   corrupting any consumer reading the JSON payload from there. Diagnostics now
   go to the shared ToolUniverse logger at DEBUG level.

3. Unsupported `db` values reported as "no results". wsearch accepts
   db=drugs/drugsSpanish/genetics/medicalTests/medicalEncyclopedia but answers
   <count>0</count> for every query against them (verified with aspirin,
   cancer, heart, BRCA1, diabetes and vitamin). The generic "document list not
   found" made that look like "your term had no match". The enum values stay
   accepted; the error now names the real cause.

All fixtures below are trimmed captures of real responses for
  https://wsearch.nlm.nih.gov/ws/query?db=healthTopics&term=leishmaniasis&rettype=...
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse import medlineplus_tool
from tooluniverse.medlineplus_tool import MedlinePlusRESTTool

pytestmark = pytest.mark.unit


_TOPIC_XML = """<?xml version="1.0" encoding="UTF-8"?>
<nlmSearchResult>
  <term>leishmaniasis</term>
  <count>1</count>
  <retstart>0</retstart>
  <retmax>10</retmax>
  <list num="1" start="0" per="10">
    <document rank="0" url="https://medlineplus.gov/leishmaniasis.html">
      <content name="healthTopic">
        <health-topic meta-desc="Leishmaniasis or leishmania, also known as Kala-azar is a parasitic disease spread by the bite of infected sand flies." title="Leishmaniasis" url="https://medlineplus.gov/leishmaniasis.html" id="3748" language="English" date-created="02/17/2004">
          <also-called>Kala-azar</also-called>
          <full-summary>&lt;p&gt;Leishmaniasis is a parasitic disease spread by the bite of infected sand flies.&lt;/p&gt;</full-summary>
          <group url="https://medlineplus.gov/infections.html" id="12">Infections</group>
          <group url="https://medlineplus.gov/skinhairandnails.html" id="18">Skin, Hair and Nails</group>
        </health-topic>
      </content>
    </document>
  </list>
</nlmSearchResult>
"""

# rettype=brief: no <health-topic> record at all, just flat content nodes.
# Matched terms are wrapped in <span class="qt0"> highlight markup.
_BRIEF_XML = """<?xml version="1.0" encoding="UTF-8"?>
<nlmSearchResult>
  <term>leishmaniasis</term>
  <count>1</count>
  <retstart>0</retstart>
  <retmax>10</retmax>
  <list num="1" start="0" per="10">
    <document rank="0" url="https://medlineplus.gov/leishmaniasis.html">
      <content name="title">&lt;span class="qt0"&gt;Leishmaniasis&lt;/span&gt;</content>
      <content name="organizationName">National Library of Medicine</content>
      <content name="altTitle">Kala-azar</content>
      <content name="FullSummary">&lt;p&gt;&lt;span class="qt0"&gt;Leishmaniasis&lt;/span&gt; is a parasitic disease spread by the bite of infected sand flies.&lt;/p&gt;</content>
      <content name="mesh">&lt;span class="qt0"&gt;Leishmaniasis&lt;/span&gt;</content>
      <content name="groupName">Infections</content>
      <content name="groupName">Skin, Hair and Nails</content>
      <content name="snippet"> &lt;span class="qt0"&gt;Leishmaniasis&lt;/span&gt; is a parasitic disease spread by the bite of infected sand flies. ... </content>
    </document>
  </list>
</nlmSearchResult>
"""

# rettype=all: the flat brief nodes AND the structured healthTopic node.
_ALL_XML = """<?xml version="1.0" encoding="UTF-8"?>
<nlmSearchResult>
  <term>leishmaniasis</term>
  <count>1</count>
  <retstart>0</retstart>
  <retmax>10</retmax>
  <list num="1" start="0" per="10">
    <document rank="0" url="https://medlineplus.gov/leishmaniasis.html">
      <content name="title">&lt;span class="qt0"&gt;Leishmaniasis&lt;/span&gt;</content>
      <content name="organizationName">National Library of Medicine</content>
      <content name="altTitle">Kala-azar</content>
      <content name="FullSummary">&lt;p&gt;&lt;span class="qt0"&gt;Leishmaniasis&lt;/span&gt; is a parasitic disease spread by the bite of infected sand flies.&lt;/p&gt;</content>
      <content name="mesh">&lt;span class="qt0"&gt;Leishmaniasis&lt;/span&gt;</content>
      <content name="groupName">Infections</content>
      <content name="groupName">Skin, Hair and Nails</content>
      <content name="healthTopic">
        <health-topic meta-desc="Leishmaniasis or leishmania, also known as Kala-azar is a parasitic disease spread by the bite of infected sand flies." title="Leishmaniasis" url="https://medlineplus.gov/leishmaniasis.html" id="3748" language="English" date-created="02/17/2004">
          <also-called>Kala-azar</also-called>
          <full-summary>&lt;p&gt;Leishmaniasis is a parasitic disease spread by the bite of infected sand flies.&lt;/p&gt;</full-summary>
          <group url="https://medlineplus.gov/infections.html" id="12">Infections</group>
          <group url="https://medlineplus.gov/skinhairandnails.html" id="18">Skin, Hair and Nails</group>
        </health-topic>
      </content>
      <content name="snippet"> &lt;span class="qt0"&gt;Leishmaniasis&lt;/span&gt; is a parasitic disease spread by the bite of infected sand flies. ... </content>
    </document>
  </list>
</nlmSearchResult>
"""

# What wsearch really answers for any query against an unserved db.
_ZERO_XML = """<?xml version="1.0" encoding="UTF-8"?>
<nlmSearchResult>
  <term>praziquantel</term>
  <count>0</count>
</nlmSearchResult>
"""

_FIXTURES = {"topic": _TOPIC_XML, "brief": _BRIEF_XML, "all": _ALL_XML}


def _tool():
    return MedlinePlusRESTTool(
        {
            "name": "MedlinePlus_search_topics_by_keyword",
            "fields": {
                "endpoint": "https://wsearch.nlm.nih.gov/ws/query?db={db}&term={term}&rettype={rettype}"
            },
            "parameter": {"properties": {"rettype": {"default": "topic"}}},
        }
    )


def _xml_resp(text):
    r = MagicMock()
    r.status_code = 200
    r.text = text
    return r


def _run(xml, arguments):
    with patch(
        "tooluniverse.medlineplus_tool.requests.get", return_value=_xml_resp(xml)
    ):
        return _tool().run(dict(arguments))


class TestAllRettypesParse:
    @pytest.mark.parametrize("rettype", ["topic", "brief", "all"])
    def test_leishmaniasis_topic_returned(self, rettype):
        result = _run(
            _FIXTURES[rettype],
            {"term": "leishmaniasis", "db": "healthTopics", "rettype": rettype},
        )

        assert "error" not in result, result
        topics = result["topics"]
        assert len(topics) == 1
        topic = topics[0]
        assert topic["title"] == "Leishmaniasis"
        assert topic["url"] == "https://medlineplus.gov/leishmaniasis.html"
        assert topic["rank"] == "0"
        assert topic["language"] == "English"
        assert topic["also_called"] == ["Kala-azar"]
        assert "parasitic disease" in topic["summary"]
        assert topic["meta_desc"]

    def test_brief_keys_match_topic_keys(self):
        args = {"term": "leishmaniasis", "db": "healthTopics"}
        brief = _run(_BRIEF_XML, dict(args, rettype="brief"))["topics"][0]
        topic = _run(_TOPIC_XML, dict(args, rettype="topic"))["topics"][0]
        assert set(brief) == set(topic)

    def test_all_parses_identically_to_topic(self):
        args = {"term": "leishmaniasis", "db": "healthTopics"}
        assert _run(_ALL_XML, dict(args, rettype="all")) == _run(
            _TOPIC_XML, dict(args, rettype="topic")
        )

    def test_brief_strips_search_highlight_markup(self):
        topic = _run(
            _BRIEF_XML,
            {"term": "leishmaniasis", "db": "healthTopics", "rettype": "brief"},
        )["topics"][0]
        assert "<span" not in json.dumps(topic)
        assert topic["groups"] == ["Infections", "Skin, Hair and Nails"]

    def test_brief_language_derived_from_spanish_db(self):
        topic = _run(
            _BRIEF_XML,
            {"term": "leishmaniasis", "db": "healthTopicsSpanish", "rettype": "brief"},
        )["topics"][0]
        assert topic["language"] == "Spanish"


class TestNoStdoutPollution:
    @pytest.mark.parametrize("rettype", ["topic", "brief", "all"])
    def test_nothing_printed_on_success(self, capsys, rettype):
        _run(
            _FIXTURES[rettype],
            {"term": "leishmaniasis", "db": "healthTopics", "rettype": rettype},
        )
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_nothing_printed_on_zero_results(self, capsys):
        _run(_ZERO_XML, {"term": "praziquantel", "db": "drugs", "rettype": "topic"})
        assert capsys.readouterr().out == ""

    def test_debug_diagnostics_still_available_via_logger(self):
        with patch.object(medlineplus_tool, "logger") as mock_logger:
            _run(
                _TOPIC_XML,
                {"term": "leishmaniasis", "db": "healthTopics", "rettype": "topic"},
            )
        assert mock_logger.debug.called


class TestUnsupportedDbErrorNamesCause:
    @pytest.mark.parametrize(
        "db", ["drugs", "drugsSpanish", "genetics", "medicalTests"]
    )
    def test_error_names_the_db_and_the_working_alternatives(self, db):
        result = _run(_ZERO_XML, {"term": "praziquantel", "db": db, "rettype": "topic"})

        error = result["error"]
        assert result["status"] == "error"
        assert db in error
        assert "healthTopics" in error
        # Not the old generic text that read as "no match for your term".
        assert error != "document list not found"

    def test_supported_db_with_no_hits_does_not_blame_the_database(self):
        result = _run(
            _ZERO_XML,
            {"term": "zzzznotaterm", "db": "healthTopics", "rettype": "topic"},
        )
        assert result["status"] == "error"
        assert "does not serve" not in result["error"]
        assert "zzzznotaterm" in result["error"]


class TestConfigMatchesReality:
    def _search_config(self):
        data = json.loads(
            (
                Path(medlineplus_tool.__file__).parent
                / "data"
                / "medlineplus_tools.json"
            ).read_text()
        )
        return next(
            c for c in data if c["name"] == "MedlinePlus_search_topics_by_keyword"
        )

    def test_rettype_description_agrees_with_schema_default(self):
        rettype = self._search_config()["parameter"]["properties"]["rettype"]
        assert rettype["default"] == "topic"
        # The description used to advertise "brief (concise information,
        # default)" while the schema default was "topic".
        assert "brief (concise information, default)" not in rettype["description"]
        assert "default: topic" in rettype["description"]

    def test_db_description_states_which_databases_are_served(self):
        config = self._search_config()
        db = config["parameter"]["properties"]["db"]
        # Enum values stay accepted -- removing them would break callers.
        assert set(db["enum"]) == {
            "healthTopics",
            "healthTopicsSpanish",
            "drugs",
            "drugsSpanish",
            "genetics",
            "medicalTests",
            "medicalEncyclopedia",
        }
        assert "zero results" in db["description"]
        assert "zero results" in config["description"]
