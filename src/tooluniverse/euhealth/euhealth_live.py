"""
EUHealth live builder: crawl the EU Health FDP and populate the local datastore.

What this script does
---------------------
1) Fetch dataset metadata from the EU Health FAIR Data Point (FDP).
2) Normalize fields into (doc_key=uuid, text, metadata, text_hash).
3) Build/extend the local `euhealth` collection:
   - upsert_collection("euhealth", embedding_model=..., embedding_dimensions=...)
   - insert_docs(...) with content de-dup (text_hash)
   - embed texts and write FAISS index

Inputs & configuration
----------------------
- EUFDP_BASE : base URL for the portal (default: https://fair.healthinformationportal.eu)
- EMBED_PROVIDER / EMBED_MODEL / EMBED_DIM : embedding backend/settings
- Optional CLI flags can override envs in your implementation.

Outputs
-------
- <user_cache_dir>/embeddings/euhealth.db
- <user_cache_dir>/embeddings/euhealth.faiss

Notes
-----
- This module is intentionally thin and reuses the general pipeline (pipeline.build_collection).
- Network hiccups are expected; implement retries.
- If you re-run frequently, only *new* documents will be inserted (dedup by (doc_key) and (text_hash)).

See also
--------
- tools_runtime.py : how the topic/deep-dive tools consume this collection
- database_setup/pipeline.py : end-to-end build helpers
"""

from __future__ import annotations
import os
import hashlib
import requests
import time
import re
import urllib3
import numpy as np
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup
from tooluniverse.database_setup.sqlite_store import SQLiteStore
from tooluniverse.database_setup.vector_store import VectorStore
from tooluniverse.database_setup.embedder import Embedder
from tooluniverse.database_setup.hf.sync_hf import db_path_for_collection
from tooluniverse.database_setup.provider_resolver import (
    resolve_provider,
    resolve_model,
)


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# -------------------
# FDP / JSON-LD config
# -------------------

FDP_BASE = os.environ.get("EUFDP_BASE", "https://fair.healthinformationportal.eu")
HEADERS = {"Accept": "application/ld+json"}
TIMEOUT = float(os.environ.get("EUFDP_TIMEOUT", "20"))

DCT = "http://purl.org/dc/terms/"
DCAT = "http://www.w3.org/ns/dcat#"
FOAF = "http://xmlns.com/foaf/0.1/"
RDFS = "http://www.w3.org/2000/01/rdf-schema#"

# -------------------
# JSON-LD normalization
# -------------------


def _vals(node: Dict, pred: str):
    """Extract (@value) text values and (@id) IRIs for a JSON-LD predicate; returns (texts, ids)."""
    txt, ids = [], []
    for v in node.get(pred, []):
        if "@value" in v:
            txt.append(str(v["@value"]).strip())
        elif "@id" in v:
            ids.append(str(v["@id"]).strip())
    return txt, ids


def _idx(graph: List[Dict]) -> Dict[str, Dict]:
    """Index JSON-LD nodes by @id for quick lookup."""
    return {n.get("@id"): n for n in graph if n.get("@id")}


def _flatten_agent_name(agent_id: str, idx: Dict[str, Dict]) -> str | None:
    """Resolve a FOAF/Agent-like node to a human-readable name (foaf:name/rdfs:label/dct:title)."""
    ag = idx.get(agent_id) or {}
    types = [t.lower() for t in ag.get("@type", [])]
    if not any("agent" in t for t in types):
        return None
    for pred in (f"{FOAF}name", f"{RDFS}label", f"{DCT}title"):
        t, _ = _vals(ag, pred)
        if t:
            return t[0]
    return None


def _select_dataset(graph: List[Dict]) -> Dict:
    """Pick the first node typed as dcat:Dataset (fallback to first node)."""
    for n in graph:
        typ = n.get("@type", [])
        if any(t.endswith("dcat#Dataset") or t == f"{DCAT}Dataset" for t in typ):
            return n
    return graph[0] if graph else {}


def normalize_jsonld(graph: List[Dict]) -> Dict:
    """Normalize a JSON-LD graph into a flat dataset dict used by the datastore builder.

    Returns fields like: title, description, keywords, themes (IRIs), language (IRIs),
    landing_page, license (IRI), spatial (IRI), publisher[], creator[], and uuid.
    """
    idx = _idx(graph)
    ds = _select_dataset(graph)

    titles, _ = _vals(ds, f"{DCT}title")
    descs, _ = _vals(ds, f"{DCT}description")
    keywords, _ = _vals(ds, f"{DCAT}keyword")
    _, themes = _vals(ds, f"{DCAT}theme")
    _, langs = _vals(ds, f"{DCT}language")

    pub_txt, pub_ids = _vals(ds, f"{DCT}publisher")
    creator_txt, creator_ids = _vals(ds, f"{DCT}creator")
    publishers = [p for p in pub_txt if p and p.lower() != "none"]
    for pid in pub_ids:
        nm = _flatten_agent_name(pid, idx)
        if nm and nm.lower() != "none":
            publishers.append(nm)
    creators = [c for c in creator_txt if c and c.lower() != "none"]
    for cid in creator_ids:
        nm = _flatten_agent_name(cid, idx)
        if nm and nm.lower() != "none":
            creators.append(nm)

    landing = (_vals(ds, f"{DCAT}landingPage")[1] or [""])[0]
    contact = (_vals(ds, f"{DCAT}contactPoint")[1] or [""])[0]
    license_iri = (_vals(ds, f"{DCT}license")[1] or [""])[0]
    spatial = (_vals(ds, f"{DCT}spatial")[1] or [""])[0]

    dataset_id = ds.get("@id", "")
    uuid = dataset_id.rsplit("/", 1)[-1] if "/dataset/" in dataset_id else dataset_id

    return {
        "uuid": uuid or dataset_id,
        "title": " | ".join(titles)[:500],
        "description": " ".join(descs)[:8000],
        "keywords": [k.strip() for k in keywords if k.strip()],
        "themes": themes,
        "language": langs,
        "license": license_iri,
        "spatial": spatial,
        "publisher": publishers,
        "creator": creators,
        "landing_page": landing,
        "contact_point": contact,
    }


# -------------------
# FDP traversal
# -------------------


def list_all_dataset_uuids() -> List[str]:
    """Enumerate dataset UUIDs from the EU Health FDP root by traversing catalogs."""
    uuids: List[str] = []
    try:
        r = requests.get(FDP_BASE, headers=HEADERS, timeout=TIMEOUT, verify=False)
        r.raise_for_status()
    except Exception as e:
        raise RuntimeError(f"Failed to fetch FDP root {FDP_BASE}: {e}")

    root_json = r.json()
    root_graph = root_json if isinstance(root_json, list) else [root_json]

    catalogs: List[str] = []
    for obj in root_graph:
        for mc in obj.get("https://w3id.org/fdp/fdp-o#metadataCatalog", []):
            cid = mc.get("@id")
            if cid and cid.startswith(f"{FDP_BASE}/catalog/"):
                catalogs.append(cid)

    if not catalogs:
        raise RuntimeError("No catalogs found in FDP root")

    for cat_url in catalogs:
        try:
            rc = requests.get(cat_url, headers=HEADERS, timeout=TIMEOUT, verify=False)
            rc.raise_for_status()
            cat_json = rc.json()
            cat_graph = cat_json if isinstance(cat_json, list) else [cat_json]

            for node in cat_graph:
                for ds in node.get("http://www.w3.org/ns/dcat#dataset", []):
                    ds_id = ds.get("@id")
                    if ds_id and ds_id.startswith(f"{FDP_BASE}/dataset/"):
                        uuids.append(ds_id.rsplit("/", 1)[-1])
        except Exception as e:
            print(f"[WARN] failed to fetch catalog {cat_url}: {e}")

    print(f" Discovered {len(uuids)} dataset UUIDs")
    return uuids


def fetch_jsonld(uuid: str) -> List[Dict]:
    """Download the JSON-LD representation for a dataset UUID from the FDP."""
    r = requests.get(
        f"{FDP_BASE}/dataset/{uuid}?format=jsonld",
        headers=HEADERS,
        timeout=TIMEOUT,
        verify=False,
    )
    r.raise_for_status()
    return r.json()


# -------------------
# Collection builder
# -------------------


def _hash_text(s: str) -> str:
    """Return a short SHA-256 hex prefix (16 chars) for content de-duplication."""
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def merge_metadata(base: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    """Merge two normalized dataset dicts: union lists, concat descriptions, prefer longest title."""
    merged = base.copy()
    # Union list fields
    for k in ["keywords", "themes", "language", "publisher", "creator"]:
        merged[k] = sorted(set(base.get(k, []) + new.get(k, [])))
    # Concatenate descriptions
    desc_a, desc_b = base.get("description", ""), new.get("description", "")
    if desc_b and desc_b not in desc_a:
        merged["description"] = (desc_a + " " + desc_b).strip()
    # Prefer the longest title
    if len(new.get("title", "")) > len(base.get("title", "")):
        merged["title"] = new["title"]
    return merged


def build_euhealth_collection(
    db_path: str | None = None,
    collection: str = "euhealth",
    embed: bool = True,
    embed_provider: str | None = None,
    embed_model: str | None = None,
    limit: int | None = None,
):
    """Crawl the EU Health FDP into a local collection and (optionally) embed.

    Steps
    -----
    1) Discover dataset UUIDs and fetch/normalize JSON-LD.
    2) Deduplicate by landing_page while merging metadata.
    3) Insert docs as (doc_key=uuid, text, metadata, text_hash).
    4) If embed=True, compute embeddings, L2-normalize, write FAISS, and update collection metadata.

    Parameters
    ----------
    db_path : Optional[str]
        Target SQLite path; defaults to <user_cache_dir>/embeddings/<collection>.db.
    collection : str, default "euhealth"
        Collection name for both SQLite and FAISS files.
    embed : bool, default True
        Compute and persist embeddings/FAISS if True.
    embed_provider, embed_model : Optional[str]
        Override provider/model resolution.
    limit : Optional[int]
        If provided, only process the first N discovered UUIDs (for testing).

    Side effects
    ------------
    - Writes/updates <collection>.db and <collection>.faiss on disk.
    - Prints progress/warnings to stdout.
    """

    db_path = db_path or db_path_for_collection(collection)
    store = SQLiteStore(db_path)

    # Initial upsert without locking model/dim yet
    store.upsert_collection(
        collection,
        description="EU Health FAIR Data Point (live → per-collection DB)",
        embedding_model=None,
        embedding_dimensions=None,
        index_type="IndexFlatIP",
    )

    uuids = list_all_dataset_uuids()
    if limit:
        uuids = uuids[:limit]

    dedupe_map: Dict[str, Dict] = {}  # landing : merged metadata

    for i, u in enumerate(uuids, 1):
        try:
            graph = fetch_jsonld(u)
            norm = normalize_jsonld(graph)

            lp = norm.get("landing_page")
            if not lp:
                continue

            if lp in dedupe_map:
                survivor = dedupe_map[lp]
                dedupe_map[lp] = merge_metadata(survivor, norm)
                print(
                    f"[MERGED] {u} | {norm['title'][:60]} "
                    f"(landing={lp}) → merged into {survivor['uuid']} | {survivor['title'][:60]}"
                )
            else:
                dedupe_map[lp] = norm

        except Exception as e:
            print(f"[WARN] {u}: {e}")
        if i % 200 == 0:
            time.sleep(0.2)
    inserted = 0
    for survivor in dedupe_map.values():
        text = "\n\n".join(
            filter(
                None,
                [
                    f"title: {survivor.get('title', '')}",
                    f"description: {survivor.get('description', '')}",
                    f"keywords: {', '.join(survivor.get('keywords', []))}",
                    f"themes: {', '.join(survivor.get('themes', []))}",
                    f"publishers: {', '.join(survivor.get('publisher', []))}",
                    f"creators: {', '.join(survivor.get('creator', []))}",
                    f"language: {', '.join(survivor.get('language', []))}",
                    f"spatial: {survivor.get('spatial', '')}",
                    f"license: {survivor.get('license', '')}",
                ],
            )
        )

        h = _hash_text(text)
        meta = {
            k: survivor.get(k, "")
            for k in [
                "uuid",
                "title",
                "keywords",
                "themes",
                "language",
                "license",
                "spatial",
                "publisher",
                "creator",
                "landing_page",
                "contact_point",
                "description",
            ]
        }

        store.insert_docs(collection, [(survivor["uuid"], text, meta, h)])
        inserted += 1

    # --- Embeddings ---
    if embed:
        rows = store.fetch_docs(collection, limit=1_000_000)
        if not rows:
            print(" No documents inserted; skipping embedding")
            return
        doc_ids = [r["id"] for r in rows]
        texts = [r["text"] for r in rows]

        prov = resolve_provider(embed_provider)
        mdl = resolve_model(prov, embed_model)

        emb = Embedder(provider=prov, model=mdl, batch_size=64)
        vecs = emb.embed(texts)
        vecs = vecs / (np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-12)
        vs = VectorStore(db_path)
        vs.load_index(collection, dim=vecs.shape[1])
        vs.add_embeddings(collection, doc_ids, vecs)

        # Now that we know the true dimension/model, persist them
        store.upsert_collection(
            collection,
            description="EU Health FAIR Data Point (live → per-collection DB)",
            embedding_model=mdl,
            embedding_dimensions=int(vecs.shape[1]),
            index_type="IndexFlatIP",
        )

    print(
        f" EUHealth collection built: docs={inserted}, deduped={len(dedupe_map)} unique landings"
    )


# -------------------
# Deep-dive (landing pages)
# -------------------

UA = "ToolUniverse-EUHealth"
LOGIN_WORDS = re.compile(
    r"\b(login|sign[ -]?in|anmelden|connexion|accedi|acceso|autenticaci[oó]n|sso|samlsso)\b",
    re.I,
)
BASE_DOMAIN = "healthinformationportal.eu"
BOILERPLATE_PATHS = {
    "/rapid-exchange-forum",
    "/health-information-europe/initiatives",
    "/activities/catalogue",
    "/about",
    "/contact",
    "/privacy-policy",
    "/terms",
}


def _head(url: str) -> Optional[requests.Response]:
    """HEAD request helper with redirects and UA; returns None on network errors."""

    try:
        return requests.head(
            url, timeout=TIMEOUT, allow_redirects=True, headers={"User-Agent": UA}
        )
    except Exception:
        return None


def _get(url: str, max_bytes: int = 262144) -> Optional[requests.Response]:
    """GET with basic streaming to cap response size; returns None on network errors."""
    try:
        r = requests.get(
            url,
            timeout=TIMEOUT,
            allow_redirects=True,
            headers={"User-Agent": UA},
            stream=True,
        )
        content = b""
        for chunk in r.iter_content(8192):
            content += chunk
            if len(content) >= max_bytes:
                break
        r._content = content
        return r
    except Exception:
        return None


def classify_link(url: str) -> Dict:
    """Classify a URL fetched from a dataset landing page.

    Returns
    -------
    dict with keys:
      - url
      - classification: "html_portal" | "login_or_error" | "error"
      - http_status?: int
      - content_type?: str
      - preview?: str | List[List[str]] (table rows or text snippet)
      - notes?: str
    """

    hr = _head(url)
    if hr is None:
        return {"url": url, "classification": "error", "notes": "HEAD failed"}

    gr = _get(url)
    if gr is None:
        return {"url": url, "classification": "error", "notes": "GET failed"}

    ctg = (gr.headers.get("Content-Type") or "").lower()

    if "text/html" in ctg:
        html = gr.text or ""
        status = gr.status_code

        BLOCK_WORDS = re.compile(
            r"(enable javascript|cookies required|verifying your browser|cloudflare|captcha)",
            re.I,
        )

        if status >= 400 or LOGIN_WORDS.search(html) or BLOCK_WORDS.search(html):
            return {
                "url": url,
                "classification": "login_or_error",
                "http_status": status,
            }

        # Good HTML: extract preview
        soup = BeautifulSoup(html, "html.parser")
        preview = None
        table = soup.find("table")
        if table:
            rows = []
            for tr in table.find_all("tr")[:5]:
                cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                rows.append(cells)
            preview = rows
        else:
            txt = soup.get_text(" ", strip=True)
            preview = txt[:500]

        return {
            "url": url,
            "classification": "html_portal",
            "http_status": status,
            "preview": preview,
        }

    # Everything else: treat as error (no other types in EU Health Database sweep)
    return {
        "url": url,
        "classification": "error",
        "content_type": ctg,
        "http_status": hr.status_code,
    }


def extract_landing_links(landing_html: str) -> List[str]:
    """Extract candidate <a href> links from landing HTML, prioritizing 'data source' anchors,
    de-duplicating, and skipping known boilerplate on the base domain.
    """

    soup = BeautifulSoup(landing_html, "html.parser")
    anchors = soup.find_all("a", href=True)
    out: List[str] = []
    for a in anchors:
        text = (a.get_text() or "").strip().lower()
        href = a["href"].strip()
        if not href.startswith("http"):
            continue
        if "data source" in text or "url of the data source" in text:
            out.insert(0, href)
        else:
            out.append(href)
    seen, filtered = set(), []
    for u in out:
        if u in seen:
            continue
        seen.add(u)
        try:
            from urllib.parse import urlparse

            p = urlparse(u)
            if p.netloc.endswith(BASE_DOMAIN) and p.path in BOILERPLATE_PATHS:
                continue
        except Exception:
            pass
        filtered.append(u)
    return filtered[:12]


def deep_dive_for_datasets(
    rows: List[Dict], max_links_per_dataset: int = 8
) -> List[Dict]:
    """Fetch each dataset’s landing page, extract and classify up to N outgoing links.

    Input
    -----
    rows : [{uuid, title, landing_page}, ...]

    Output
    ------
    [{ uuid, title, landing_page, candidates: [ {url, classification, ...}, ... ] }, ...]
    """

    results: List[Dict] = []
    for row in rows:
        lp = row.get("landing_page")
        entry = {
            "uuid": row.get("uuid"),
            "title": row.get("title"),
            "landing_page": lp,
            "candidates": [],
        }
        if not lp or not str(lp).startswith("http"):
            results.append(entry)
            continue
        gr = _get(lp)
        if not gr or "text/html" not in (
            (gr.headers.get("Content-Type") or "").lower()
        ):
            results.append(entry)
            continue
        links = extract_landing_links(gr.text)[:max_links_per_dataset]
        classified = [classify_link(url) for url in links]
        order = {"html_portal": 0, "login_or_error": 1, "error": 2}
        classified.sort(key=lambda c: order.get(c.get("classification", "error"), 99))
        entry["candidates"].extend(classified[:max_links_per_dataset])
        time.sleep(0.25)
        results.append(entry)
    return results


# -------------------
# Entrypoint
# -------------------

if __name__ == "__main__":
    build_euhealth_collection(limit=int(os.getenv("EUHEALTH_LIMIT", "0") or 0) or None)
