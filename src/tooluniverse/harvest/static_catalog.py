from __future__ import annotations

import math
import re
from copy import deepcopy
from dataclasses import dataclass
from typing import Dict, Iterable, List, Set
from urllib.parse import urlparse

from .domain_policies import trust_score
from .ranker import rank_candidates


# -----------------------------------------------------------------------------
# Static catalog data
# -----------------------------------------------------------------------------

RAW_CATALOG: List[Dict[str, object]] = [
    {
        "name": "ClinicalTrials.gov Study Fields API",
        "url": "https://clinicaltrials.gov/api/query/study_fields",
        "doc_url": "https://clinicaltrials.gov/api/gui/home",
        "description": "Query structured fields from the ClinicalTrials.gov registry covering study design, enrollment, outcomes, and locations.",
        "keywords": ["clinical", "trial", "study", "research", "ctgov", "clinicaltrials"],
        "category": "clinical_trials",
        "base_score": 0.95,
        "endpoints": [
            {"method": "GET", "path": "/api/query/study_fields", "summary": "Query study fields"},
            {"method": "GET", "path": "/api/query/full_studies", "summary": "Fetch full study records"},
        ],
    },
    {
        "name": "NCI Clinical Trials API",
        "url": "https://clinicaltrialsapi.cancer.gov/api/v1/clinical-trials",
        "doc_url": "https://clinicaltrialsapi.cancer.gov",
        "description": "REST API exposing cancer clinical trials curated by the National Cancer Institute (NCI) with filters across disease, stage, and therapy.",
        "keywords": ["clinical", "trial", "oncology", "cancer", "nci", "research"],
        "category": "clinical_trials",
        "base_score": 0.88,
        "endpoints": [
            {"method": "GET", "path": "/api/v1/clinical-trials", "summary": "Search cancer clinical trials"},
            {"method": "GET", "path": "/api/v1/diseases", "summary": "List disease terms"},
        ],
    },
    {
        "name": "FDA OpenFDA Drug Label API",
        "url": "https://api.fda.gov/drug/label.json",
        "doc_url": "https://open.fda.gov/apis/drug/label/",
        "description": "OpenFDA drug labeling information with pharmacology, indications, warnings, and dosage guidance.",
        "keywords": ["drug", "label", "fda", "pharmaceutical", "medication", "clinical"],
        "category": "pharmacovigilance",
        "base_score": 0.6,
        "endpoints": [
            {"method": "GET", "path": "/drug/label.json", "summary": "Query drug labeling records"},
            {"method": "GET", "path": "/drug/event.json", "summary": "Retrieve drug adverse events"},
        ],
    },
    {
        "name": "FDA OpenFDA Adverse Events API",
        "url": "https://api.fda.gov/drug/event.json",
        "doc_url": "https://open.fda.gov/apis/drug/event/",
        "description": "Adverse event case reports submitted to FDA FAERS with patient outcomes and drug role details.",
        "keywords": ["adverse", "event", "pharmacovigilance", "drug safety", "faers"],
        "category": "pharmacovigilance",
        "base_score": 0.65,
        "endpoints": [
            {"method": "GET", "path": "/drug/event.json", "summary": "Search FAERS adverse event data"},
        ],
    },
    {
        "name": "FDA OpenFDA Device Recall API",
        "url": "https://api.fda.gov/device/recall.json",
        "doc_url": "https://open.fda.gov/apis/device/recall/",
        "description": "Medical device recall records including classification, recall reason, and event dates.",
        "keywords": ["medical device", "recall", "fda", "safety", "compliance"],
        "category": "device_safety",
        "base_score": 0.55,
        "endpoints": [
            {"method": "GET", "path": "/device/recall.json", "summary": "Retrieve device recall records"},
        ],
    },
    {
        "name": "CDC Socrata Open Data API",
        "url": "https://data.cdc.gov/resource/9mfq-cb36.json",
        "doc_url": "https://dev.socrata.com/foundry/data.cdc.gov/9mfq-cb36",
        "description": "CDC curated datasets accessible via the Socrata Open Data API, including COVID-19 cases and vaccinations.",
        "keywords": ["cdc", "public health", "covid", "vaccination", "socrata", "open data"],
        "category": "public_health",
        "base_score": 0.86,
        "endpoints": [
            {"method": "GET", "path": "/resource/<dataset>.json", "summary": "Query CDC open datasets"},
        ],
    },
    {
        "name": "CDC PLACES Community Health API",
        "url": "https://chronicdata.cdc.gov/resource/cwsq-ngmh.json",
        "doc_url": "https://dev.socrata.com/foundry/chronicdata.cdc.gov/cwsq-ngmh",
        "description": "Model-based estimates for chronic disease, health risk factors, and preventive services at local levels; supports community health assessments and dental health overlays.",
        "keywords": ["community health", "chronic disease", "behavioral health", "cdc", "oral health"],
        "category": "public_health",
        "base_score": 0.8,
        "endpoints": [
            {"method": "GET", "path": "/resource/cwsq-ngmh.json", "summary": "Retrieve PLACES health estimates"},
        ],
    },
    {
        "name": "CDC Oral Health Data Portal API",
        "url": "https://data.cdc.gov/resource/4nhi-4p9m.json",
        "doc_url": "https://dev.socrata.com/foundry/data.cdc.gov/4nhi-4p9m",
        "description": "Community oral health indicators including dental visits, sealant prevalence, and fluoridation coverage for dentistry analytics.",
        "keywords": ["oral health", "dentistry", "dental", "fluoride", "sealant", "cdc"],
        "category": "dentistry",
        "base_score": 0.81,
        "endpoints": [
            {"method": "GET", "path": "/resource/4nhi-4p9m.json", "summary": "Query oral health indicator records"},
        ],
    },
    {
        "name": "WHO Global Health Observatory API",
        "url": "https://ghoapi.azureedge.net/api/Indicator",
        "doc_url": "https://www.who.int/data/gho/info/gho-odata-api",
        "description": "World Health Organization indicators covering global health metrics, vaccination, and disease burden.",
        "keywords": ["who", "global health", "indicator", "vaccination", "disease surveillance"],
        "category": "global_health",
        "base_score": 0.87,
        "endpoints": [
            {"method": "GET", "path": "/api/Indicator", "summary": "List WHO health indicators"},
            {"method": "GET", "path": "/api/Indicator?$filter", "summary": "Filter indicators by code"},
        ],
    },
    {
        "name": "NIH RePORTER Projects API",
        "url": "https://api.reporter.nih.gov/v2/projects/search",
        "doc_url": "https://api.reporter.nih.gov/",
        "description": "NIH-funded research projects with abstracts, funding amounts, and investigator information.",
        "keywords": ["nih", "grants", "research", "project", "biomedical"],
        "category": "research_funding",
        "base_score": 0.83,
        "endpoints": [
            {"method": "POST", "path": "/v2/projects/search", "summary": "Search NIH-funded projects"},
        ],
    },
    {
        "name": "NCBI E-utilities ESummary API",
        "url": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
        "doc_url": "https://www.ncbi.nlm.nih.gov/books/NBK25500/",
        "description": "Programmatic access to NCBI databases including PubMed, nucleotide, protein, and ClinVar content.",
        "keywords": ["ncbi", "genomics", "pubmed", "sequence", "biomedical"],
        "category": "genomics",
        "base_score": 0.84,
        "endpoints": [
            {"method": "GET", "path": "/entrez/eutils/esearch.fcgi", "summary": "Search NCBI databases"},
            {"method": "GET", "path": "/entrez/eutils/esummary.fcgi", "summary": "Retrieve database summaries"},
        ],
    },
    {
        "name": "Ensembl REST API",
        "url": "https://rest.ensembl.org/info/ping",
        "doc_url": "https://rest.ensembl.org",
        "description": "Genomics REST service for Ensembl data including genes, variants, and comparative genomics with JSON outputs.",
        "keywords": ["ensembl", "genomics", "variants", "gene", "rest service", "bioinformatics"],
        "category": "genomics",
        "base_score": 0.8,
        "endpoints": [
            {"method": "GET", "path": "/lookup/id/{id}", "summary": "Lookup Ensembl gene or transcript"},
            {"method": "GET", "path": "/overlap/region/{species}/{region}", "summary": "Fetch features overlapping a region"},
        ],
    },
    {
        "name": "SAMHSA Behavioral Health Treatment Services Locator API",
        "url": "https://findtreatment.samhsa.gov/locator",
        "doc_url": "https://findtreatment.samhsa.gov/developers",
        "description": "Behavioral health treatment provider directory with search by service type, payment, and location.",
        "keywords": ["mental health", "treatment", "behavioral health", "samhsa"],
        "category": "mental_health",
        "base_score": 0.81,
        "endpoints": [
            {"method": "GET", "path": "/locator", "summary": "Search behavioral health providers"},
        ],
    },
    {
        "name": "USDA FoodData Central API",
        "url": "https://api.nal.usda.gov/fdc/v1/foods/search",
        "doc_url": "https://fdc.nal.usda.gov/api-guide.html",
        "description": "Nutrient composition data for branded and experimental foods, with search and detail endpoints.",
        "keywords": ["nutrition", "food", "dietary", "usda", "nutrients"],
        "category": "nutrition",
        "base_score": 0.79,
        "endpoints": [
            {"method": "POST", "path": "/fdc/v1/foods/search", "summary": "Search foods by keyword"},
            {"method": "GET", "path": "/fdc/v1/food/{fdcId}", "summary": "Retrieve nutrient profile"},
        ],
    },
    {
        "name": "CDC Vaccination Coverage API",
        "url": "https://data.cdc.gov/resource/8xkx-amqh.json",
        "doc_url": "https://dev.socrata.com/foundry/data.cdc.gov/8xkx-amqh",
        "description": "US vaccination coverage estimates by vaccine and demographic segment.",
        "keywords": ["vaccination", "immunization", "cdc", "coverage", "public health"],
        "category": "vaccination",
        "base_score": 0.8,
        "endpoints": [
            {"method": "GET", "path": "/resource/8xkx-amqh.json", "summary": "Vaccination coverage records"},
        ],
    },
    {
        "name": "NOAA Climate Data Online API",
        "url": "https://www.ncdc.noaa.gov/cdo-web/api/v2/datasets",
        "doc_url": "https://www.ncdc.noaa.gov/cdo-web/webservices/v2",
        "description": "Climate and weather datasets from NOAA including temperature, precipitation, and extremes for environmental monitoring and early warning systems.",
        "keywords": ["environment", "environmental", "weather", "climate", "noaa", "meteorology", "monitoring"],
        "category": "environmental",
        "base_score": 0.78,
        "endpoints": [
            {"method": "GET", "path": "/cdo-web/api/v2/datasets", "summary": "List NOAA datasets"},
            {"method": "GET", "path": "/cdo-web/api/v2/data", "summary": "Query climate observations"},
        ],
    },
    {
        "name": "EPA AirNow API",
        "url": "https://www.airnowapi.org/aq/data/",
        "doc_url": "https://docs.airnowapi.org/",
        "description": "Air quality measurements and forecasts for US monitoring stations, including pollutants and AQI, supporting environmental monitoring pipelines.",
        "keywords": ["air quality", "environment", "environmental", "epa", "pollution", "aqi", "monitoring"],
        "category": "environmental",
        "base_score": 0.77,
        "endpoints": [
            {"method": "GET", "path": "/aq/data/", "summary": "Retrieve air quality data"},
        ],
    },
    {
        "name": "Orphanet Rare Disease API",
        "url": "https://www.orpha.net/OrphAPI/api/Disease",
        "doc_url": "https://api.orphanet.net/OrphAPI/#!/Disease",
        "description": "Rare disease catalog with Orpha codes, synonyms, epidemiology, and classification.",
        "keywords": ["rare disease", "orphanet", "orpha", "genetic", "registry"],
        "category": "rare_disease",
        "base_score": 0.76,
        "endpoints": [
            {"method": "GET", "path": "/OrphAPI/api/Disease", "summary": "List rare diseases"},
            {"method": "GET", "path": "/OrphAPI/api/Disease/{OrphaCode}", "summary": "Retrieve disease details"},
        ],
    },
    {
        "name": "RAREDISEASES.info NIH Service",
        "url": "https://rarediseases.info.nih.gov/services/v1/diseases",
        "doc_url": "https://rarediseases.info.nih.gov/developers",
        "description": "NIH Genetic and Rare Diseases (GARD) API providing disease descriptions, symptoms, and resources.",
        "keywords": ["rare disease", "nih", "gard", "genetic", "registry"],
        "category": "rare_disease",
        "base_score": 0.75,
        "endpoints": [
            {"method": "GET", "path": "/services/v1/diseases", "summary": "Search rare diseases"},
        ],
    },
    {
        "name": "USAFacts COVID-19 API",
        "url": "https://api.usafacts.org/covid/covid-api/v1/cases",
        "doc_url": "https://usafacts.org/visualizations/coronavirus-covid-19-spread-map/api/",
        "description": "County-level COVID-19 cases and deaths in the United States with daily updates.",
        "keywords": ["covid", "pandemic", "surveillance", "epidemiology"],
        "category": "pandemic",
        "base_score": 0.74,
        "endpoints": [
            {"method": "GET", "path": "/covid/covid-api/v1/cases", "summary": "Retrieve COVID-19 cases"},
        ],
    },
    {
        "name": "Global.Health Line List API",
        "url": "https://covid19-api.global.health/v1/line-list",
        "doc_url": "https://global.health/documentation/api",
        "description": "Anonymized global case line lists for pathogen surveillance, including demographics and travel history.",
        "keywords": ["pandemic", "outbreak", "surveillance", "line list", "global health"],
        "category": "pandemic",
        "base_score": 0.73,
        "endpoints": [
            {"method": "GET", "path": "/v1/line-list", "summary": "Retrieve outbreak line list"},
        ],
    },
    {
        "name": "OpenFDA Food Enforcement API",
        "url": "https://api.fda.gov/food/enforcement.json",
        "doc_url": "https://open.fda.gov/apis/food/enforcement/",
        "description": "Food recall enforcement reports with product description, reason, and distribution data.",
        "keywords": ["food", "recall", "fda", "safety", "enforcement"],
        "category": "food_safety",
        "base_score": 0.55,
        "endpoints": [
            {"method": "GET", "path": "/food/enforcement.json", "summary": "Search food recall enforcement"},
        ],
    },
    {
        "name": "USDA National Farmers Market Directory API",
        "url": "https://search.ams.usda.gov/farmersmarkets/v1/data.svc/zipSearch",
        "doc_url": "https://www.ams.usda.gov/services/local-regional/food-directories-datasets",
        "description": "Directory of US farmers markets with location, operation schedule, and services.",
        "keywords": ["nutrition", "food access", "farmers market", "usda"],
        "category": "nutrition",
        "base_score": 0.7,
        "endpoints": [
            {"method": "GET", "path": "/farmersmarkets/v1/data.svc/zipSearch", "summary": "Find farmers markets by ZIP"},
        ],
    },
    {
        "name": "HealthData.gov CKAN Catalog API",
        "url": "https://healthdata.gov/api/3/action/package_search",
        "doc_url": "https://healthdata.gov/developer",
        "description": "Catalog of US Department of Health and Human Services datasets via CKAN API.",
        "keywords": ["open data", "catalog", "health data", "ckan", "metadata"],
        "category": "data_catalog",
        "base_score": 0.82,
        "endpoints": [
            {"method": "GET", "path": "/api/3/action/package_search", "summary": "Search dataset catalog"},
        ],
    },
    {
        "name": "data.gov CKAN Catalog API",
        "url": "https://catalog.data.gov/api/3/action/package_search",
        "doc_url": "https://catalog.data.gov/dataset",
        "description": "US Federal data catalog with metadata across climate, energy, health, and finance.",
        "keywords": ["open data", "catalog", "federal", "ckan", "metadata"],
        "category": "data_catalog",
        "base_score": 0.8,
        "endpoints": [
            {"method": "GET", "path": "/api/3/action/package_search", "summary": "Search the federal data catalog"},
        ],
    },
    {
        "name": "Europe PMC RESTful API",
        "url": "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
        "doc_url": "https://europepmc.org/RestfulWebService",
        "description": "Biomedical literature, grants, and patents from Europe PMC with advanced search syntax.",
        "keywords": ["literature", "research", "biomedical", "europe pmc", "publications"],
        "category": "literature",
        "base_score": 0.78,
        "endpoints": [
            {"method": "GET", "path": "/webservices/rest/search", "summary": "Search biomedical literature"},
        ],
    },
    {
        "name": "OpenAlex Graph API",
        "url": "https://api.openalex.org/works",
        "doc_url": "https://docs.openalex.org/api",
        "description": "Scholarly works, authors, concepts, and institutions graph with filtering for literature discovery and citation analysis.",
        "keywords": ["literature", "openalex", "scholarly", "citations", "research graph"],
        "category": "literature",
        "base_score": 0.77,
        "endpoints": [
            {"method": "GET", "path": "/works", "summary": "Search scholarly works"},
            {"method": "GET", "path": "/authors", "summary": "Browse scholarly authors"},
        ],
    },
]


# -----------------------------------------------------------------------------
# Internal helpers
# -----------------------------------------------------------------------------

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> Set[str]:
    tokens = set(TOKEN_PATTERN.findall((text or "").lower()))
    enriched: Set[str] = set(tokens)
    for tok in tokens:
        if len(tok) <= 2:
            continue
        if tok.endswith("ies") and len(tok) > 3:
            enriched.add(tok[:-3] + "y")
        if tok.endswith("ing") and len(tok) > 4:
            enriched.add(tok[:-3])
        if tok.endswith("al") and len(tok) > 4:
            enriched.add(tok[:-2])
        if tok.endswith("s") and len(tok) > 3:
            enriched.add(tok[:-1])
    return enriched


@dataclass(frozen=True)
class CatalogRecord:
    data: Dict[str, object]
    tokens: Set[str]
    keyword_tokens: Set[str]
    base_score: float


def _prepare_catalog(raw_items: Iterable[Dict[str, object]]) -> List[CatalogRecord]:
    prepared: List[CatalogRecord] = []
    for item in raw_items:
        entry = deepcopy(item)

        url = str(entry.get("url") or "").strip()
        if not url:
            continue
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        entry.setdefault("host", host)
        entry.setdefault("base_url", base_url)
        entry.setdefault("source", "static_catalog")
        entry.setdefault("doc_url", entry.get("doc_url") or f"{base_url}/")
        entry.setdefault("health", {"ok": True, "status": 200, "latency_ms": 180, "checked": "static"})
        entry.setdefault("cors", {"preflight": False})
        entry.setdefault("trust", trust_score(host))

        keywords = entry.get("keywords") or []
        if keywords:
            desc = entry.get("description") or ""
            kw_text = "; ".join(str(k) for k in keywords)
            if kw_text and kw_text.lower() not in desc.lower():
                entry["description"] = f"{desc} (keywords: {kw_text})"
        keyword_tokens = _tokenize(" ".join(map(str, keywords)))
        text_tokens = _tokenize(" ".join(
            str(part) for part in (
                entry.get("name", ""),
                entry.get("description", ""),
                entry.get("category", ""),
                entry.get("doc_url", ""),
            )
        ))

        base_score = float(entry.get("base_score") or 0.0)

        prepared.append(
            CatalogRecord(
                data=entry,
                tokens=text_tokens | keyword_tokens,
                keyword_tokens=keyword_tokens,
                base_score=base_score,
            )
        )

    return prepared


CATALOG: List[CatalogRecord] = _prepare_catalog(RAW_CATALOG)


# -----------------------------------------------------------------------------
# Public harvester interface
# -----------------------------------------------------------------------------

def _score_entry(tokens: Set[str], record: CatalogRecord) -> float:
    if not tokens:
        return record.base_score + 0.5

    keyword_overlap = len(tokens & record.keyword_tokens)
    text_overlap = len(tokens & record.tokens)

    if keyword_overlap == 0 and text_overlap == 0:
        return record.base_score * 0.1

    precision = keyword_overlap / (len(tokens) or 1)
    coverage = (keyword_overlap + text_overlap) / (len(record.tokens) or 1)

    return (
        2.0 * keyword_overlap
        + 1.2 * text_overlap
        + 1.5 * precision
        + 1.0 * coverage
        + record.base_score * 0.25
    )


SYNONYM_MAP = {
    "clinical": ["trial", "research"],
    "dentistry": ["dental", "oral", "oralhealth"],
    "dental": ["dentistry", "oral", "oralhealth"],
    "oral": ["dentistry", "dental", "oralhealth"],
    "environmental": ["environment", "climate", "monitoring"],
    "environment": ["environmental", "climate", "air"],
    "monitoring": ["surveillance", "tracking"],
    "rare": ["orphan", "orphanet", "genetic"],
    "disease": ["condition", "illness"],
    "genomics": ["genomic", "gene", "sequence", "dna"],
    "genomic": ["genomics", "gene", "dna"],
    "pandemic": ["outbreak", "surveillance"],
    "surveillance": ["monitoring", "tracking"],
    "nutrition": ["food", "diet", "dietary"],
    "vaccination": ["immunization", "vaccine"],
    "mental": ["behavioral", "behavior", "psych"],
    "health": ["healthcare", "publichealth"],
    "pharmaceutical": ["drug", "medicine"],
    "adverse": ["safety", "pharmacovigilance"],
}


def harvest(query: str, limit: int = 5, **kwargs) -> List[Dict[str, object]]:
    """
    Harvest candidate API endpoints from the static catalog.

    Args:
        query: Natural language search string.
        limit: Maximum number of candidates to return.
        **kwargs: Unused passthrough parameters for compatibility.
    """
    limit = max(1, min(int(limit or 5), 50))
    query = (query or "").strip()

    if not CATALOG:
        return []

    if not query:
        top = sorted(CATALOG, key=lambda rec: rec.base_score, reverse=True)[:limit]
        return [deepcopy(rec.data) for rec in top]

    token_union: Set[str] = _tokenize(query)
    for token in list(token_union):
        for syn in SYNONYM_MAP.get(token, []):
            token_union |= _tokenize(syn)

    scored: List[Dict[str, object]] = []
    for record in CATALOG:
        score = _score_entry(token_union, record)
        if score <= 0 and record.base_score <= 0:
            continue
        candidate = deepcopy(record.data)
        candidate["_match_score"] = round(score, 4)
        candidate["_match_terms"] = sorted(token_union & record.tokens)
        scored.append(candidate)

    if not scored:
        top = sorted(CATALOG, key=lambda rec: rec.base_score, reverse=True)[:limit]
        return [deepcopy(rec.data) for rec in top]

    preliminary = sorted(scored, key=lambda c: c["_match_score"], reverse=True)[: limit * 3]
    ranked = rank_candidates(query, preliminary)
    final = ranked[:limit]

    for cand in final:
        cand.pop("_match_score", None)
        cand.pop("_match_terms", None)

    return final


__all__ = ["harvest"]
