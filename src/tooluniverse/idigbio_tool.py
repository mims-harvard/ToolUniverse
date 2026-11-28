"""
iDigBio tools for ToolUniverse — biodiversity specimen records.

iDigBio aggregates digitized biodiversity specimen records (museum, herbarium,
paleo collections) in Darwin Core format. These tools search those records by
taxon/locality, summarise them, and retrieve a single record.

The legacy iDigBio search API that these tools used to call, search.idigbio.org/v2,
was retired: every path now answers HTTP 410 with "The legacy iDigBio API has been
retired. Data remains available through https://idigbio.gbif.us and the GBIF API."
iDigBio's holdings are therefore reached here through the GBIF occurrence API,
restricted to GBIF's iDigBio network, which is the same data the hosted portal at
idigbio.gbif.us serves.

GBIF is not a drop-in replacement, and three of its behaviours silently produce a
wrong answer rather than an error. Each is guarded below, with the reading that
established it:

  * GBIF IGNORES a query parameter it does not know, and answers as if the filter
    were absent. `notAParam=zzz` returns the full 89,279,963-record network count.
  * `genus`, `family`, `order`, `class` and `phylum` are NOT occurrence-search
    filters. Passing them is the case above: `genus=Panthera` returned all
    89,279,963 records. A higher taxon has to be resolved to a `taxonKey` first.
  * `species/match?name=Panthera&rank=GENUS` does not fail when it cannot match
    at that rank -- it climbs, returning matchType=HIGHERRANK, rank=KINGDOM,
    usageKey=1 (Animalia), whose taxonKey selects 44,405,370 records. The
    rank-specific spelling, `species/match?genus=Panthera`, returns
    matchType=EXACT, rank=GENUS, usageKey=2435194. Only an exact match at the
    requested rank is used.
  * `country` takes an ISO 3166-1 alpha-2 code. The spellings iDigBio accepted
    return no error and no records: "United States", "USA" and "us" each
    answered count=0 where "US" answers 51,443,270. Country values are resolved
    against GBIF's own country enumeration before use.

All readings above are from 2026-11-27.

API: https://api.gbif.org/v1  (public, no authentication, JSON)
Portal: https://idigbio.gbif.us
"""

from typing import Any, Dict, List, Optional, Tuple

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

GBIF_BASE = "https://api.gbif.org/v1"
# GBIF's network for iDigBio; what idigbio.gbif.us is a view of.
IDIGBIO_NETWORK_KEY = "68e8e67a-43e6-44a3-8817-dc0e6b70f973"

# Darwin-Core query fields users may filter on. Each maps to a GBIF occurrence
# search parameter that was verified to actually narrow the result set.
_DIRECT_FIELDS = {
    "scientificname": "scientificName",
    "country": "country",  # resolved to ISO 3166-1 alpha-2 first
    "stateprovince": "stateProvince",
    "recordedby": "recordedBy",
    "catalognumber": "catalogNumber",
    "collectioncode": "collectionCode",
}
# Higher taxa, broadest first. GBIF has no occurrence filter for these, so each
# is resolved to a taxonKey; the order is also the nesting order used to check
# that several of them can hold at once.
_TAXON_RANKS = ("phylum", "class", "order", "family", "genus")
_QUERY_FIELDS = tuple(_DIRECT_FIELDS) + _TAXON_RANKS

# iDigBio's summary facet names, mapped to the GBIF facets that carry the same
# counts. GBIF names a facet after its own field, and a facet on a name it does
# not know comes back as an empty list rather than refused -- indistinguishable
# from "no record has this field". Every name on the right was asked for against
# the live API on 2026-11-27 and answered with counts.
_FACET_FIELDS = {
    "scientificname": "scientificName",
    "genus": "genusKey",
    "family": "familyKey",
    "order": "orderKey",
    "class": "classKey",
    "phylum": "phylumKey",
    "country": "country",
    "stateprovince": "stateProvince",
    "recordedby": "recordedBy",
    "catalognumber": "catalogNumber",
    "collectioncode": "collectionCode",
    "basisofrecord": "basisOfRecord",
    "datasetkey": "datasetKey",
    "institutioncode": "institutionCode",
    "year": "year",
}

_countries_cache: Optional[Dict[str, str]] = None


def _error(message: str, **extra: Any) -> Dict[str, Any]:
    out = {"status": "error", "error": message}
    out.update(extra)
    return out


def _gbif_get(path: str, params: Dict[str, Any], timeout: int):
    """GET a GBIF endpoint, returning (payload, error_envelope).

    Exactly one of the two is non-None; the error envelope is the standard
    {"status": "error", ...} dict so callers never raise.
    """
    try:
        resp = requests.get(
            f"{GBIF_BASE}{path}",
            params=params,
            headers={"Accept": "application/json"},
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json(), None
    except requests.exceptions.Timeout:
        return None, _error(f"GBIF request timed out after {timeout}s")
    except requests.exceptions.RequestException as e:
        return None, _error(f"GBIF request failed: {e}")
    except ValueError:
        return None, _error("GBIF returned a non-JSON response")


def _resolve_country(value: str, timeout: int) -> Tuple[Optional[str], Optional[Dict]]:
    """Turn a country name, alpha-3 or alpha-2 into the alpha-2 GBIF filters on.

    GBIF answers an unrecognised country with zero records and no error, so a
    value it would not recognise is refused here instead.
    """
    global _countries_cache
    wanted = value.strip()
    if not wanted:
        return None, _error("country must not be blank", parameter="country")
    if _countries_cache is None:
        payload, err = _gbif_get("/enumeration/country", {}, timeout)
        if err is not None:
            return None, err
        table: Dict[str, str] = {}
        for row in payload if isinstance(payload, list) else []:
            iso2 = row.get("iso2")
            if not iso2:
                continue
            for spelling in (
                row.get("iso2"),
                row.get("iso3"),
                row.get("title"),
                row.get("enumName"),
            ):
                if isinstance(spelling, str) and spelling:
                    table[spelling.strip().casefold()] = iso2
        _countries_cache = table
    code = _countries_cache.get(wanted.casefold())
    if code is None:
        return None, _error(
            f"GBIF does not recognise the country {value!r}. Use an ISO 3166-1 "
            "name or code, for example 'United States', 'USA' or 'US'.",
            parameter="country",
        )
    return code, None


def _resolve_taxa(
    asked: Dict[str, str], timeout: int
) -> Tuple[Optional[int], Optional[Dict], Dict[str, Any]]:
    """Resolve the higher taxa asked for to the one taxonKey to filter on.

    Returns (taxon_key, error_envelope, resolution). GBIF ORs repeated taxonKey
    values while iDigBio's rq ANDed its fields, so several ranks cannot simply be
    handed over together. They nest, so the narrowest rank implies the broader
    ones: the narrowest is used as the filter and the broader ones are checked
    against the ancestry GBIF reports for it. A combination no taxon satisfies is
    reported rather than quietly widened to the narrowest rank alone.
    """
    resolution: Dict[str, Any] = {}
    matches: Dict[str, Dict[str, Any]] = {}
    for rank in _TAXON_RANKS:
        value = asked.get(rank)
        if not value:
            continue
        payload, err = _gbif_get("/species/match", {rank: value}, timeout)
        if err is not None:
            return None, err, resolution
        match = payload if isinstance(payload, dict) else {}
        if (
            match.get("matchType") != "EXACT"
            or str(match.get("rank", "")).casefold() != rank
        ):
            return (
                None,
                _error(
                    f"GBIF has no exact {rank} named {value!r} "
                    f"(it answered matchType={match.get('matchType')!r}, "
                    f"rank={match.get('rank')!r}). Check the spelling, or filter "
                    "with scientificname instead.",
                    parameter=rank,
                ),
                resolution,
            )
        matches[rank] = match
        resolution[rank] = {
            "name": match.get("canonicalName") or value,
            "taxon_key": match.get("usageKey"),
            "rank": match.get("rank"),
        }
    if not matches:
        return None, None, resolution
    narrowest = [r for r in _TAXON_RANKS if r in matches][-1]
    chosen = matches[narrowest]
    for rank, match in matches.items():
        if rank == narrowest:
            continue
        if chosen.get(f"{rank}Key") != match.get("usageKey"):
            return (
                None,
                _error(
                    f"No taxon is both {rank} {asked[rank]!r} and {narrowest} "
                    f"{asked[narrowest]!r}: GBIF places {asked[narrowest]!r} in "
                    f"{rank} {chosen.get(rank)!r}.",
                    parameter=rank,
                ),
                resolution,
            )
    return chosen.get("usageKey"), None, resolution


def _build_query(
    arguments: Dict[str, Any], timeout: int
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict], Dict[str, Any]]:
    """Build the GBIF occurrence query, returning (params, error, resolution)."""
    if arguments.get("rq"):
        return (
            None,
            _error(
                "'rq' was iDigBio's own query language and the API that read it "
                "has been retired. Use the named fields instead: "
                + ", ".join(_QUERY_FIELDS)
                + ".",
                parameter="rq",
            ),
            {},
        )
    asked = {
        f: arguments[f].strip()
        for f in _QUERY_FIELDS
        if isinstance(arguments.get(f), str) and arguments[f].strip()
    }
    if not asked:
        return (
            None,
            _error("Provide at least one query field: " + ", ".join(_QUERY_FIELDS)),
            {},
        )
    params: Dict[str, Any] = {"networkKey": IDIGBIO_NETWORK_KEY}
    for field, value in asked.items():
        if field not in _DIRECT_FIELDS:
            continue
        if field == "country":
            code, err = _resolve_country(value, timeout)
            if err is not None:
                return None, err, {}
            params["country"] = code
        else:
            params[_DIRECT_FIELDS[field]] = value
    taxon_key, err, resolution = _resolve_taxa(asked, timeout)
    if err is not None:
        return None, err, resolution
    if taxon_key is not None:
        params["taxonKey"] = taxon_key
    return params, None, {"query": asked, "taxa_resolved": resolution}


def _summarize(item: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten a GBIF occurrence to the fields the iDigBio summary carried."""
    return {
        "gbif_id": item.get("key") or item.get("gbifID"),
        "scientific_name": item.get("scientificName"),
        "family": item.get("family"),
        "genus": item.get("genus"),
        "taxon_rank": item.get("taxonRank"),
        "country": item.get("country"),
        "state_province": item.get("stateProvince"),
        "county": item.get("county"),
        "recorded_by": item.get("recordedBy"),
        "catalog_number": item.get("catalogNumber"),
        "collection_code": item.get("collectionCode"),
        "occurrence_id": item.get("occurrenceID"),
        "dataset_key": item.get("datasetKey"),
    }


def _media_summary(item: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten a GBIF occurrence's first media entry the way iDigBio's media index did."""
    media = item.get("media")
    first = media[0] if isinstance(media, list) and media else {}
    if not isinstance(first, dict):
        first = {}
    return {
        "gbif_id": item.get("key") or item.get("gbifID"),
        "type": first.get("type"),
        "format": first.get("format"),
        "title": first.get("title"),
        "creator": first.get("creator"),
        "rights_owner": first.get("rightsHolder"),
        "usage_terms": first.get("license"),
        "access_uri": first.get("identifier") or first.get("references"),
        "publisher": first.get("publisher"),
        "media_count": len(media) if isinstance(media, list) else 0,
        "scientific_name": item.get("scientificName"),
    }


@register_tool("iDigBioSearchTool")
class iDigBioSearchTool(BaseTool):
    """Search iDigBio specimen records (records / media) and summary facets.

    Dispatch is driven by ``fields.mode``:
      - unset / "records" : occurrence records in GBIF's iDigBio network (default)
      - "media"           : the same, restricted to records carrying an image
      - "summary"         : the exact total plus GBIF facet counts
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("fields", {}).get("timeout", 30)
        self.mode = tool_config.get("fields", {}).get("mode", "records")

    @staticmethod
    def _pagination(arguments: Dict[str, Any]):
        limit = arguments.get("limit", 10)
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= 100
        ):
            return (
                None,
                None,
                _error("limit must be an integer between 1 and 100", parameter="limit"),
            )
        offset = arguments.get("offset", 0)
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            return (
                None,
                None,
                _error("offset must be a non-negative integer", parameter="offset"),
            )
        return limit, offset, None

    @staticmethod
    def _search_result(
        payload: Any,
        meta: Dict[str, Any],
        limit: int,
        offset: int,
        summarizer,
    ):
        if not isinstance(payload, dict) or not isinstance(
            payload.get("results", []), list
        ):
            return _error("GBIF returned an unexpected search payload")
        items = payload.get("results", []) or []
        data = [summarizer(it) for it in items if isinstance(it, dict)]
        total = payload.get("count")
        total_is_exact = (
            isinstance(total, int) and not isinstance(total, bool) and total >= 0
        )
        if not total_is_exact:
            total = None
        has_more = offset + len(items) < total if total_is_exact else None
        truncated = offset > 0 or has_more is True or not total_is_exact
        return {
            "status": "success",
            "data": data,
            "metadata": {
                "total_available": total,
                "total_available_is_exact": total_is_exact,
                "returned": len(data),
                "limit": limit,
                "offset": offset,
                "has_more": has_more,
                "next_offset": offset + len(items) if has_more else None,
                "truncated": truncated,
                "result_set_complete": not truncated,
                "source": "iDigBio via the GBIF API",
                "network_key": IDIGBIO_NETWORK_KEY,
                **meta,
            },
        }

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if self.mode == "summary":
            return self._run_summary(arguments)
        if self.mode == "media":
            return self._run_media(arguments)
        return self._run_records(arguments)

    def _search(self, arguments: Dict[str, Any], extra: Dict[str, Any], summarizer):
        # Pagination is checked first so a bad limit or offset is refused without
        # a request; resolving a taxon name costs a round trip of its own.
        limit, offset, pagination_error = self._pagination(arguments)
        if pagination_error is not None:
            return pagination_error
        params, err, meta = _build_query(arguments, self.timeout)
        if err is not None:
            return err
        params.update(extra)
        params["limit"] = limit
        params["offset"] = offset
        payload, err = _gbif_get("/occurrence/search", params, self.timeout)
        if err is not None:
            return err
        return self._search_result(payload, meta, limit, offset, summarizer)

    def _run_records(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return self._search(arguments, {}, _summarize)

    def _run_media(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return self._search(arguments, {"mediaType": "StillImage"}, _media_summary)

    def _run_summary(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        params, err, meta = _build_query(arguments, self.timeout)
        if err is not None:
            return err

        top_fields = arguments.get("top_fields")
        if isinstance(top_fields, list):
            top_fields = ",".join(str(f) for f in top_fields if f)
        requested: List[str] = []
        if isinstance(top_fields, str) and top_fields.strip():
            requested = [f.strip() for f in top_fields.split(",") if f.strip()]

        unknown = [f for f in requested if f.casefold() not in _FACET_FIELDS]
        if unknown:
            return _error(
                "GBIF cannot facet on "
                + ", ".join(repr(f) for f in unknown)
                + ". It answers an unknown facet with an empty list rather than "
                "an error, so these are refused here. Available: "
                + ", ".join(sorted(_FACET_FIELDS))
                + ".",
                parameter="top_fields",
            )

        params["limit"] = 0
        if requested:
            try:
                count = max(1, min(int(arguments.get("count") or 10), 100))
            except (TypeError, ValueError):
                count = 10
            params["facet"] = [_FACET_FIELDS[f.casefold()] for f in requested]
            params["facetLimit"] = count

        payload, err = _gbif_get("/occurrence/search", params, self.timeout)
        if err is not None:
            return err
        if not isinstance(payload, dict):
            return _error("GBIF returned an unexpected summary payload")

        facets: Dict[str, Any] = {}
        # GBIF echoes a facet's name in SCREAMING_SNAKE ("GENUS_KEY" for the
        # "genusKey" that was asked for), so the echo is normalised before the
        # counts are matched back. A name that failed to match would produce an
        # empty breakdown, which reads as "no data" rather than as a bug.
        returned = {
            str(entry.get("field", "")).casefold().replace("_", ""): entry
            for entry in payload.get("facets") or []
            if isinstance(entry, dict)
        }
        for field in requested:
            gbif_name = _FACET_FIELDS[field.casefold()]
            entry = returned.get(gbif_name.casefold())
            counts = entry.get("counts") if isinstance(entry, dict) else None
            facets[field] = {
                str(c.get("name")): c.get("count")
                for c in counts or []
                if isinstance(c, dict)
            }

        return {
            "status": "success",
            "data": {"itemCount": payload.get("count"), "facets": facets},
            "metadata": {
                "top_fields": ",".join(requested) if requested else None,
                "gbif_facets": [_FACET_FIELDS[f.casefold()] for f in requested],
                "source": "iDigBio via the GBIF API",
                "network_key": IDIGBIO_NETWORK_KEY,
                **meta,
            },
        }


@register_tool("iDigBioRecordTool")
class iDigBioRecordTool(BaseTool):
    """Retrieve a single iDigBio specimen record by its GBIF occurrence key."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("fields", {}).get("timeout", 30)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        raw = arguments.get("occurrence_key")
        if raw is None:
            raw = arguments.get("uuid")
        key = str(raw or "").strip()
        if not key:
            return _error("'occurrence_key' is required")
        if "-" in key:
            return _error(
                f"{key!r} looks like a legacy iDigBio record UUID. Those ids "
                "lived only in the retired search.idigbio.org API and GBIF "
                "cannot resolve them. Find the record again with "
                "iDigBio_search_records (by catalognumber, scientificname or "
                "recordedby) and use the gbif_id it returns.",
                parameter="occurrence_key",
            )
        if not key.isdigit():
            return _error(
                "'occurrence_key' must be a GBIF occurrence key, which is a "
                "number. iDigBio_search_records returns one as gbif_id.",
                parameter="occurrence_key",
            )

        try:
            resp = requests.get(
                f"{GBIF_BASE}/occurrence/{key}",
                headers={"Accept": "application/json"},
                timeout=self.timeout,
            )
            if resp.status_code == 404:
                return {
                    "status": "success",
                    "data": {},
                    "metadata": {
                        "query_key": key,
                        "note": f"No GBIF occurrence '{key}'.",
                    },
                }
            resp.raise_for_status()
            rec = resp.json()
        except requests.exceptions.Timeout:
            return _error(f"GBIF request timed out after {self.timeout}s")
        except requests.exceptions.RequestException as e:
            return _error(f"GBIF request failed: {e}")
        except ValueError:
            return _error("GBIF returned a non-JSON response")

        if not isinstance(rec, dict) or not (rec.get("key") or rec.get("gbifID")):
            return {"status": "success", "data": {}, "metadata": {"query_key": key}}
        in_network = IDIGBIO_NETWORK_KEY in (rec.get("networkKeys") or [])
        summary = _summarize(rec)
        summary["data"] = rec  # the full GBIF occurrence, verbatim
        return {
            "status": "success",
            "data": summary,
            "metadata": {
                "query_key": key,
                "in_idigbio_network": in_network,
                "source": "iDigBio via the GBIF API",
                "network_key": IDIGBIO_NETWORK_KEY,
            },
        }
