"""
EU Health Information Portal runtime utilities: topic search and deep-dive.

What this module does
---------------------
- Exposes ~20 topic search helpers defined by `TOPICS` (e.g., cancer, vaccination, mental health).
- Shapes results from the local `euhealth` collection into a stable schema for agents.
- Provides `euhealthinfo_deepdive(...)` to classify outgoing links from dataset landing pages.

Dependencies
------------
- Assumes the `euhealth` collection (SQLite + FAISS) already exists at:
  <user_cache_dir>/embeddings/euhealth.db and euhealth.faiss.
  You can either:
  (a) download the shared/official build, or
  (b) build your own with any embedding model/provider.

Search method behavior (very important)
---------------------------------------
- Public tools accept `method="keyword"|"embedding"|"hybrid"` (default "hybrid").
- If the local `euhealth` library is the **shared/official build** (embedded with
  `text-embedding-3-small`) then:
    * embedding/hybrid are **allowed** only when the caller resolves to **Azure + text-embedding-3-small**,
    * otherwise we **force `"keyword"`** (no error; tools still return results).
- If the local `euhealth` library was **built by the user** with any other model/provider,
  the requested method is **honored** (no forcing).

Practical outcomes
------------------
- No `.env` or a non-matching env (not Azure + text-embedding-3-small): tools fall back to keyword automatically.
- Matching env (Azure + text-embedding-3-small): embedding and hybrid work as requested.
- Custom local build (any model/provider): embedding/hybrid/keyword all work as requested.

Result schema (summary)
-----------------------
{
  "uuid": str,
  "title": str,
  "landing_page": str,
  "license": str | null,
  "keywords": List[str],
  "themes": List[str],         # stored as URIs, case-insensitive matching
  "language": List[str] | null,
  "spatial": str | null,
  "snippet": str               # first ~N chars of text
}

Case-insensitive themes
-----------------------
The EU FDP encodes themes as lower-cased URIs while topic specs use upper-case ontology prefixes
(e.g., "NCIT_", "DOID_"). Filtering is implemented case-insensitively to avoid false negatives.

Public API
----------
- TOPICS: Dict[str, dict]
    Each entry defines: seed terms, optional theme prefixes, and default limits.
- euhealthinfo_search_<topic>(..., method="hybrid", top_k=25, language=None, country=None, term_override=None)
    Runs search against the `euhealth` collection and returns shaped dataset summaries.
- euhealthinfo_deepdive(uuids=None, topic=None, links_per=3, method="hybrid", limit=10)
    For each dataset UUID (or top-N from a topic), inspects landing pages and classifies outgoing links:
    {"url", "classification": "direct_file" | "html_portal" | "login_or_error" | "error" | "unknown",
     "http_status"?, "content_type"?, "notes"?}

Notes
-----
- De-duplication by dataset UUID is applied when merging keyword/embedding hits.
- Network access is required only for `deepdive` (to fetch landing pages).
- If someone bypasses these tools and hits `SearchEngine` directly, the fallback rule won’t apply.

See also
--------
- euhealth_live.py         : builder script that creates `euhealth` docs and vectors
- tooluniverse/data/euhealth_tools.json : tool registration
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from tooluniverse.database_setup.search import SearchEngine
from tooluniverse.database_setup.provider_resolver import (
    resolve_provider,
    resolve_model,
)
from tooluniverse.euhealth.euhealth_live import deep_dive_for_datasets
from tooluniverse.database_setup.sqlite_store import SQLiteStore, normalize_text
from tooluniverse.utils import get_user_cache_dir
import os

# -----------------
# Topic definitions
# -----------------
TOPICS: Dict[str, Dict[str, Any]] = {
    "euhealthinfo_search_cancer": {
        "terms": ["cancer", "oncology", "tumor", "tumour", "neoplasm"],
        "themes": ["NCIT_", "DOID_"],
    },
    "euhealthinfo_search_cancer_registry": {
        "terms": ["cancerregistry", "incidence", "prevalence", "mortality", "survival"],
        "themes": ["NCIT_", "DOID_"],
    },
    "euhealthinfo_search_deaths": {
        "terms": ["deaths", "mortality", "allcausemortality", "deathstatistics"],
        "themes": [],
    },
    "euhealthinfo_search_causes_of_death": {
        "terms": ["causeofdeath", "causesofdeath", "icd", "mortalitycauses"],
        "themes": ["IDO_", "DOID_"],
    },
    "euhealthinfo_search_births": {
        "terms": ["births", "natality", "birthrate", "perinatal"],
        "themes": [],
    },
    "euhealthinfo_search_infectious_diseases": {
        "terms": [
            "infectiousdisease",
            "communicabledisease",
            "epidemic",
            "surveillance",
        ],
        "themes": ["IDO_", "OBI_", "MONDO_"],
    },
    "euhealthinfo_search_covid_19": {
        "terms": [
            "covid19",
            "coronavirus",
            "sarscov2",
            "pandemic",
            "seroprevalence",
            "wastewater",
        ],
        "themes": ["COVIDO_", "MONDO_", "DOID_"],
    },
    "euhealthinfo_search_healthcare_expenditure": {
        "terms": ["healthexpenditure", "healthspending", "healthcosts", "financing"],
        "themes": [],
    },
    "euhealthinfo_search_diabetes_mellitus_epidemiology_registry": {
        "terms": [
            "diabetes",
            "type1",
            "type2",
            "gestational",
            "registry",
            "epidemiology",
        ],
        "themes": ["EFO_", "DOID_"],
    },
    "euhealthinfo_search_hospital_in_patient_data": {
        "terms": [
            "hospitalinpatient",
            "hospitalisation",
            "admissions",
            "beds",
            "staylength",
        ],
        "themes": ["OMIT_", "EFO_"],
    },
    "euhealthinfo_search_population_health_survey": {
        "terms": [
            "populationhealthsurvey",
            "healthinterviewsurvey",
            "his",
            "hes",
            "ehis",
        ],
        "themes": ["OMIT_", "EFO_"],
    },
    "euhealthinfo_search_key_indicators_registries_surveys": {
        "terms": ["keyindicators", "registries", "surveys", "publichealthprofiles"],
        "themes": [],
    },
    "euhealthinfo_search_surveillance_mortality_rates": {
        "terms": ["surveillance", "mortalityrates", "deathmonitoring"],
        "themes": ["IDO_", "DOID_"],
    },
    "euhealthinfo_search_surveillance": {
        "terms": ["surveillance", "monitoring", "sentinel", "longitudinal"],
        "themes": ["IDO_", "OBI_"],
    },
    "euhealthinfo_search_primary_care_workforce": {
        "terms": [
            "primarycare",
            "generalpractice",
            "gp",
            "paediatrics",
            "gynaecology",
            "workforce",
            "staffing",
        ],
        "themes": [],
    },
    "euhealthinfo_search_obesity": {
        "terms": [
            "obesity",
            "bmi",
            "overweight",
            "lifestyle",
            "riskfactors",
            "nutrition",
            "physicalactivity",
        ],
        "themes": ["OMIT_", "EFO_"],
    },
    "euhealthinfo_search_vaccination": {
        "terms": [
            "vaccination",
            "immunisation",
            "immunization",
            "vaccinecoverage",
            "adversereactions",
        ],
        "themes": ["VO_", "EFO_"],
    },
    "euhealthinfo_search_mental_health": {
        "terms": [
            "mentalhealth",
            "depression",
            "anxiety",
            "wellbeing",
            "psychological",
            "psychiatric",
        ],
        "themes": ["OMIT_", "EFO_"],
    },
    "euhealthinfo_search_disability": {
        "terms": [
            "disability",
            "impairment",
            "functionallimitation",
            "accessibility",
            "qualityofcare",
        ],
        "themes": ["OMIT_", "EFO_"],
    },
    "euhealthinfo_search_alcohol_tobacco_psychoactive_use": {
        "terms": [
            "alcohol",
            "tobacco",
            "smoking",
            "vaping",
            "psychoactive",
            "addiction",
            "drugabuse",
            "substanceuse",
        ],
        "themes": ["SCDO_", "GSSO_"],
    },
}

# -----------------
# Search utilities
# -----------------
_se: Optional[SearchEngine] = None


def _se_singleton() -> SearchEngine:
    global _se
    if _se is None:
        default_db = os.path.join(get_user_cache_dir(), "embeddings", "euhealth.db")
        _se = SearchEngine(db_path=default_db)
    return _se


def _shape_from_datastore(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    shaped = []
    for r in rows:
        meta = r.get("metadata") or {}
        shaped.append(
            {
                "uuid": meta.get("uuid") or r.get("doc_key"),
                "title": meta.get("title") or (r.get("text") or "")[:120],
                "landing_page": meta.get("landing_page", ""),
                "license": meta.get("license", ""),
                "keywords": meta.get("keywords", []),
                "themes": meta.get("themes", []),
                "language": meta.get("language", []),
                "spatial": meta.get("spatial", ""),
                "snippet": (r.get("text") or "")[:280],
            }
        )
    return shaped


def _match_country(
    spatial: str, want: str, title: str = "", keywords: Optional[List[str]] = None
) -> bool:
    s = (spatial or "").lower()
    w = (want or "").lower().strip()
    if not w:
        return True
    if s == w or s.endswith(f"/{w}") or w in s:
        return True
    if w in (title or "").lower():
        return True
    if any(w in (kw or "").lower() for kw in (keywords or [])):
        return True
    return False


def _match_language(langs: Optional[List[str]], want: str) -> bool:
    if not want:
        return True
    w = want.lower().strip()
    for lang in langs or []:
        lang_norm = (lang or "").lower()
        # exact, substring, or IRI tail match
        if lang_norm == w or w in lang_norm or lang_norm.endswith(f"/{w}"):
            return True
    return False


def _topic_search(
    topic: str,
    limit: int = 25,
    top_k: int = 25,
    method: str = "hybrid",
    alpha: float = 0.5,
    country: str = "",
    language: str = "",
    term_override: str = "",
) -> List[Dict[str, Any]]:
    """
    Topic search helper.

    Parameters (common)
    -------------------
    limit : int = 25
        Max number of summaries to return.
    top_k : int = 25
        how many hits per seed term to pull from SearchEngine before dedupe.
    method : str = "hybrid"
        "keyword" | "embedding" | "hybrid". May be coerced to "keyword" for the shared build
        when the caller is not Azure + "text-embedding-3-small".
    language : Optional[str]
        Filter by language code ("en", "de", ...), if present in metadata.
    country : Optional[str]
        Filter by spatial/country metadata ("Germany", "France", ...).
    term_override : Optional[str]
        Override to the seed terms defined in TOPICS["cancer"]["terms"].

    Returns
    -------
    List[dict] in the standard summary schema (see module docstring).

    Matching
    --------
    - Keyword: FTS5 over text.
    - Embedding: FAISS IP on L2-normalized vectors.
    - Hybrid: convex blend of keyword + embedding (alpha in [0,1]).
    - Themes: case-insensitive `startswith` against stored theme URIs.
    - Method may be auto-forced to "keyword" per the shared-build rule (see module docstring).
    """
    # Enforce shared-build fallback rule
    actual_method = _maybe_force_keyword(method)

    method = actual_method

    spec = TOPICS[topic]
    se = _se_singleton()

    # Use override if provided, otherwise the topic seeds
    terms = (
        [normalize_text(term_override)]
        if term_override
        else [normalize_text(t) for t in spec["terms"]]
    )

    results = []
    for t in terms:
        results.extend(
            se.search_collection("euhealth", t, method=method, top_k=top_k, alpha=alpha)
        )

    if spec.get("themes"):
        filtered = []
        for r in results:
            meta = r.get("metadata") or {}
            if isinstance(meta, str):
                import json

                try:
                    meta = json.loads(meta)
                except Exception:
                    meta = {}
            themes = meta.get("themes") or []
            # keep docs without themes, or with matching substrings
            if not themes or any(
                th.lower() in str(x).lower() for x in themes for th in spec["themes"]
            ):
                filtered.append(r)
        results = filtered

    # Deduplicate
    seen, out = set(), []
    for r in results:
        uid = r["metadata"].get("uuid") or r.get("doc_key")
        if uid not in seen:
            seen.add(uid)
            out.append(r)

    shaped = _shape_from_datastore(out)

    if country:
        shaped = [
            s
            for s in shaped
            if _match_country(
                s.get("spatial", ""), country, s.get("title", ""), s.get("keywords", [])
            )
        ]

    if language:
        shaped = [s for s in shaped if _match_language(s.get("language", []), language)]

    result = shaped[:limit]
    return result


# We consider the "shared/official" euhealth build to be the one embedded with text-embedding-3-small.
# (Provider is assumed Azure for that build; we only allow emb/hybrid if caller is Azure+that model.)
_SHARED_MODEL_NAME = "text-embedding-3-small"


def _euhealth_db_path() -> str:
    return os.path.join(get_user_cache_dir(), "embeddings", "euhealth.db")


def _read_euhealth_embedding_model() -> str | None:
    """Read collections.embedding_model for 'euhealth' (None if missing)."""
    dbp = _euhealth_db_path()
    if not os.path.exists(dbp):
        return None
    try:
        st = SQLiteStore(dbp)
        cur = st.conn.execute(
            "SELECT embedding_model FROM collections WHERE name=? LIMIT 1",
            ("euhealth",),
        )
        row = cur.fetchone()
        return (row[0] or None) if row else None
    except Exception:
        return None


def _caller_is_azure_small() -> bool:
    prov = (resolve_provider(None) or "").strip().lower()
    mdl = (resolve_model(prov, None) or "").strip().lower()
    return prov == "azure" and mdl == _SHARED_MODEL_NAME


def _env_supports_fts5() -> bool:
    import sqlite3

    try:
        con = sqlite3.connect(":memory:")
        con.execute("CREATE VIRTUAL TABLE t USING fts5(x)")
        return True
    except Exception:
        return False


def _maybe_force_keyword(method: str) -> str:
    """
    Enforce the shared-build compatibility rule.

    Rule:
    - If local `euhealth` is the shared/official build (embedding_model == "text-embedding-3-small"):
        * allow 'embedding' or 'hybrid' ONLY when the resolved caller is Azure + "text-embedding-3-small"
        * otherwise force 'keyword' (silent fallback)
    - If local `euhealth` is a custom build (any other model/provider, or missing model tag):
        * honor the requested method (no forcing)
    - Enforce runtime FTS5 availability (Codex-safe)
    - If euhealth.db is missing, all topic tools return a warning with empty results.

    This guarantees downloaded builds always work out of the box, while still letting
    advanced users build with any provider/model and keep full embedding/hybrid functionality.
    """
    if not os.path.exists(_euhealth_db_path()):
        return "missing_db"

    # 1. If runtime cannot do FTS5 → embedding/hybrid MUST fall back
    if method in ("embedding", "hybrid") and not _env_supports_fts5():
        return "keyword"

    if method == "keyword":
        return method

    model = (_read_euhealth_embedding_model() or "").strip().lower()
    is_shared = model == _SHARED_MODEL_NAME

    if not is_shared:
        # Custom local build — all good, use requested method
        return method

    # Shared build — only allow if caller is Azure + text-embedding-3-small
    return method if _caller_is_azure_small() else "keyword"


# -----------------
# Public API
# -----------------
def euhealthinfo_deepdive(
    uuids: Optional[List[str]] = None,
    topic: Optional[str] = None,
    limit: int = 10,
    links_per: int = 3,
    method: str = "hybrid",
    alpha: float = 0.5,
    top_k: int = 25,
    country: str = "",
    language: str = "",
    term_override: str = "",
) -> List[Dict[str, Any]]:
    """
    Classify outgoing links for a set of EU Health datasets.

    Args
    ----
    uuids:
        Explicit dataset UUIDs to inspect. If None, you must provide `topic`.
    topic:
        Name of a topic function (e.g., "euhealthinfo_search_cancer").
        When provided, the top `limit` seeds from that topic are resolved to UUIDs first.
    links_per:
        Max number of outgoing links to classify per dataset.
    method:
        Search method used when resolving from `topic` ("keyword" | "embedding" | "hybrid").
        May be coerced to "keyword" for the shared/official build unless the caller is
        Azure + "text-embedding-3-small".
    limit:
        Number of seeds to retrieve when `topic` is used.

    Returns
    -------
    dict
        {
          "datasets": [
            {
              "uuid": "...",
              "title": "...",
              "candidates": [
                {"url": "...", "classification": "direct_file", "http_status": 200, "content_type": "text/csv"},
                ...
              ]
            }, ...
          ]
        }

    Classification notes
    --------------------
    - "html_portal": Navigational portals or API consoles.
    - "login_or_error": 401/403/404 or obvious login walls.
    - "error"/"unknown": network failures or ambiguous responses.

    Raises
    ------
    ValueError if both `uuids` and `topic` are None.
    """

    if uuids:
        rows = _se_singleton().fetch_docs("euhealth", doc_keys=uuids, limit=len(uuids))
        shaped = _shape_from_datastore(rows)
        # keep caller order
        shaped.sort(
            key=lambda x: uuids.index(x["uuid"]) if x["uuid"] in uuids else 10**9
        )
        return deep_dive_for_datasets(
            [
                {
                    "uuid": s["uuid"],
                    "title": s["title"],
                    "landing_page": s["landing_page"],
                }
                for s in shaped
            ],
            max_links_per_dataset=links_per,
        )

    if topic and topic in TOPICS:
        method = _maybe_force_keyword(method)  # enforce before resolving seed
        if method == "missing_db":
            return {
                "warning": (
                    "EUHealth datastore not found locally (euhealth.db missing).\n"
                    "Please download or build the euhealth collection.\n"
                    "To install the official datastore:\n"
                    "  export HF_TOKEN=YOUR_HF_TOKEN\n"
                    '  tu-datastore sync-hf download --repo "agenticx/tooluniverse-datastores" --collection euhealth --overwrite\n'
                ),
                "results": [],
            }
        seeds = _topic_search(
            topic,
            limit=limit,
            method=method,
            alpha=alpha,
            country=country,
            language=language,
            term_override=term_override,
            top_k=top_k,
        )
        return deep_dive_for_datasets(
            [
                {
                    "uuid": s["uuid"],
                    "title": s["title"],
                    "landing_page": s["landing_page"],
                }
                for s in seeds
            ],
            max_links_per_dataset=links_per,
        )

    return [{"error": "Provide euhealth UUIDs or a valid topic name."}]


# -----------------
# Dynamic export
# -----------------
__all__ = list(TOPICS.keys()) + ["euhealthinfo_deepdive"]
globals_ns = globals()
for _fname in TOPICS.keys():

    def _maker(name: str):
        def _fn(
            limit: int = 25,
            method: str = "hybrid",
            alpha: float = 0.5,
            top_k: int = 25,
            country: str = "",
            language: str = "",
            term_override: str = "",
        ):
            # --- enforce fallback BEFORE SearchEngine is ever touched ---
            actual_method = _maybe_force_keyword(method)
            if actual_method == "missing_db":
                return {
                    "warning": (
                        "EUHealth datastore not found locally (euhealth.db missing).\n"
                        "Please download or build the euhealth collection.\n"
                        "To install the official datastore:\n"
                        "  export HF_TOKEN=YOUR_HF_TOKEN\n"
                        '  tu-datastore sync-hf download --repo "agenticx/tooluniverse-datastores" --collection euhealth --overwrite\n'
                    ),
                    "results": [],
                }

            if actual_method != method:
                # run keyword version
                results = _topic_search(
                    name,
                    limit=limit,
                    method=actual_method,
                    alpha=alpha,
                    top_k=top_k,
                    country=country,
                    language=language,
                    term_override=term_override,
                )
                return {
                    "warning": (
                        f"Requested '{method}' is not available without Azure + text-embedding-3-small. "
                        f"Falling back to '{actual_method}'."
                    ),
                    "results": results,
                }

            # Normal case (no fallback)
            return _topic_search(
                name,
                limit=limit,
                method=method,
                alpha=alpha,
                top_k=top_k,
                country=country,
                language=language,
                term_override=term_override,
            )

        _fn.__name__ = name
        _fn.__doc__ = f"Topic search over EUHealth shared datastore: {name}"
        return _fn

    globals_ns[_fname] = _maker(_fname)
