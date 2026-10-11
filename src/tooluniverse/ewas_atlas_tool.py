# ewas_atlas_tool.py
"""
EWAS Atlas tools for ToolUniverse.

EWAS Atlas (NGDC/CNCB, Beijing) is a curated knowledgebase of
epigenome-wide association studies: which CpG probes were reported for which
trait, in which study, cohort and tissue. It overlaps with the EWAS Catalog
(MRC-IEU) but is curated and served independently, so it still answers when
the Catalog is down (ewascatalog.org answered HTTP 503 site-wide on
2026-10-05, 10-08 and 10-09).

API: https://ngdc.cncb.ac.cn/ewas/rest (documented at /ewas/api).
No authentication required. Behaviour verified live on 2026-10-09:

* Every response is ``{"code": 0|1, "msg": ..., "data": ...}``; ``code: 1``
  with ``data: null`` means "not found" for study and publication lookups.
* An unknown probe ID, or a chromosome written as "X"/"chrX", makes the
  server close the connection without a response instead of answering.
  Chromosomes are numbers: X is 23, Y is 24.
* Coordinates are GRCh37/hg19.
* ``/pos`` answers a 1 Mb window in about 20 s (~550 probes); a 5 Mb window
  hits the server's own ~60 s limit and comes back truncated, so the window
  is capped at 1 Mb here.
* Study and publication records spell their association list
  ``assocaitionList``; both spellings are read.
"""

from collections import Counter
from typing import Any, Dict, List, Optional

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

EWAS_ATLAS_URL = "https://ngdc.cncb.ac.cn/ewas/rest"
MAX_REGION_BP = 1_000_000
_CHROMOSOME_NUMBERS = {"X": 23, "Y": 24}


def _limit(value: Any, default: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return default
    return min(value, maximum)


def _chromosome(value: Any) -> Optional[int]:
    """'chr5' / '5' / 5 -> 5, 'X' -> 23, 'Y' -> 24; None if unrecognised."""
    text = str(value if value is not None else "").strip().upper()
    if text.startswith("CHR"):
        text = text[3:]
    if text in _CHROMOSOME_NUMBERS:
        return _CHROMOSOME_NUMBERS[text]
    if text.isdigit() and 1 <= int(text) <= 24:
        return int(text)
    return None


def _association(raw: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "study_id": raw.get("studyId"),
        "trait": raw.get("trait"),
        "correlation": raw.get("correlation"),
        "rank": raw.get("rank"),
        "pmid": str(raw["pmid"]) if raw.get("pmid") is not None else None,
    }


def _probe(raw: Dict[str, Any], max_associations: int) -> Dict[str, Any]:
    """Flatten one probe record and bound its association list."""
    associations = [
        _association(a) for a in raw.get("associationList") or [] if isinstance(a, dict)
    ]
    genes = []
    for transcript in raw.get("relatedTranscription") or []:
        name = transcript.get("geneName") if isinstance(transcript, dict) else None
        if name and name not in genes:
            genes.append(name)
    return {
        "probe_id": raw.get("probeId"),
        "chromosome": raw.get("chrHg19"),
        "position_hg19": raw.get("posHg19"),
        "cpg_island": raw.get("cpgIsland"),
        "genes": genes,
        "association_count": len(associations),
        "trait_count": len({a["trait"] for a in associations if a["trait"]}),
        "associations": associations[:max_associations],
    }


def _top_traits(raw_probes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    counts = Counter(
        a.get("trait")
        for raw in raw_probes
        for a in raw.get("associationList") or []
        if isinstance(a, dict) and a.get("trait")
    )
    return [{"trait": t, "associations": n} for t, n in counts.most_common(15)]


def _study(raw: Dict[str, Any], max_associations: int) -> Dict[str, Any]:
    associations = raw.get("assocaitionList") or raw.get("associationList") or []
    rows = [
        {
            "probe_id": a.get("probeId"),
            "correlation": a.get("correlation"),
            "rank": a.get("rank"),
            "p_value": a.get("pvalue") or None,
        }
        for a in associations
        if isinstance(a, dict)
    ]
    cohorts = [
        {
            "stage": c.get("stage"),
            "cohort": c.get("fullName") or c.get("cohortName") or None,
            "sample_size": c.get("sampleSize"),
            "tissue": c.get("tissue"),
            "platform": c.get("platform"),
            "description": c.get("description") or None,
            "mean_age": c.get("meanAge"),
            "male_fraction": c.get("malePercentage"),
        }
        for c in raw.get("cohortList") or []
        if isinstance(c, dict)
    ]
    return {
        "study_id": raw.get("studyId"),
        "reported_trait": raw.get("reportedTrait"),
        "case_group": raw.get("caseGroup") or None,
        "control_group": raw.get("controlGroup") or None,
        "description": raw.get("otherDescription") or None,
        "association_count": len(rows),
        "associations": rows[:max_associations],
        "cohorts": cohorts,
    }


@register_tool("EWASAtlasTool")
class EWASAtlasTool(BaseTool):
    """Look up EWAS Atlas probes, genes, regions, studies and publications."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 90)
        self.operation = tool_config.get("fields", {}).get("operation", "get_probe")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        handler = {
            "get_probe": self._get_probe,
            "search_by_gene": self._search_by_gene,
            "search_by_region": self._search_by_region,
            "get_study": self._get_study,
            "get_publication": self._get_publication,
        }.get(self.operation)
        if handler is None:
            return {"status": "error", "error": f"Unknown operation: {self.operation}"}
        try:
            return handler(arguments or {})
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"EWAS Atlas did not answer within {self.timeout}s.",
                "retryable": True,
            }
        except requests.exceptions.ConnectionError:
            if self.operation == "get_probe":
                return {
                    "status": "error",
                    "error": "EWAS Atlas closed the connection. It does this for "
                    "probe IDs it does not hold (e.g. non-Illumina IDs), so check "
                    "the ID; otherwise retry later.",
                }
            return {
                "status": "error",
                "error": "Failed to connect to EWAS Atlas.",
                "retryable": True,
            }
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            return {"status": "error", "error": f"EWAS Atlas returned HTTP {code}"}
        except ValueError:
            return {
                "status": "error",
                "error": "EWAS Atlas returned an incomplete or non-JSON response.",
                "retryable": True,
            }

    def _fetch(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        response = requests.get(
            f"{EWAS_ATLAS_URL}/{path}", params=params, timeout=self.timeout
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("unexpected payload")
        return payload

    @staticmethod
    def _required(arguments: Dict[str, Any], name: str, example: str):
        value = str(arguments.get(name) or "").strip()
        if not value:
            return None, {
                "status": "error",
                "error": f"{name} is required, e.g. '{example}'.",
            }
        return value, None

    def _get_probe(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        probe_id, error = self._required(arguments, "probe_id", "cg05575921")
        if error:
            return error
        payload = self._fetch("probe", {"probeId": probe_id})
        raw = payload.get("data")
        if payload.get("code") != 0 or not isinstance(raw, dict):
            return {
                "status": "error",
                "error": f"EWAS Atlas has no probe '{probe_id}': {payload.get('msg')}",
            }
        probe = _probe(raw, _limit(arguments.get("limit"), 50, 500))
        return {
            "status": "success",
            "data": probe,
            "metadata": {
                "source": "EWAS Atlas (NGDC)",
                "returned_associations": len(probe["associations"]),
                "note": "Coordinates are GRCh37/hg19. 'rank' is the probe's rank "
                "within that study's reported results.",
            },
        }

    def _probe_list(self, raw_probes, arguments, query):
        max_probes = _limit(arguments.get("limit"), 50, 500)
        per_probe = _limit(arguments.get("max_associations_per_probe"), 10, 200)
        raw_probes = [p for p in raw_probes if isinstance(p, dict)]
        raw_probes.sort(key=lambda p: -len(p.get("associationList") or []))
        probes = [_probe(p, per_probe) for p in raw_probes[:max_probes]]
        return {
            "status": "success",
            "data": probes,
            "metadata": {
                **query,
                "source": "EWAS Atlas (NGDC)",
                "total_probes": len(raw_probes),
                "returned_probes": len(probes),
                "total_associations": sum(
                    len(p.get("associationList") or []) for p in raw_probes
                ),
                "top_traits": _top_traits(raw_probes),
                "note": "Probes are ordered by number of reported associations. "
                "Each probe lists at most max_associations_per_probe of them; "
                "association_count is the full number. Coordinates are "
                "GRCh37/hg19.",
            },
        }

    def _search_by_gene(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        gene, error = self._required(arguments, "gene_symbol", "AHRR")
        if error:
            return error
        payload = self._fetch("gene", {"geneSymbol": gene})
        data = payload.get("data") if payload.get("code") == 0 else None
        raw_probes = (data or {}).get("probeList") or []
        if not raw_probes:
            return {
                "status": "success",
                "data": [],
                "metadata": {
                    "gene_symbol": gene,
                    "source": "EWAS Atlas (NGDC)",
                    "total_probes": 0,
                    "note": "No EWAS Atlas probes are annotated to this gene. "
                    "Check the official HGNC symbol.",
                },
            }
        return self._probe_list(raw_probes, arguments, {"gene_symbol": gene})

    def _search_by_region(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        chromosome = _chromosome(arguments.get("chromosome"))
        if chromosome is None:
            return {
                "status": "error",
                "error": "chromosome must be 1-22, X or Y (e.g. '5' or 'chr5').",
            }
        start, end = arguments.get("start"), arguments.get("end")
        if (
            isinstance(start, bool)
            or isinstance(end, bool)
            or not isinstance(start, int)
            or not isinstance(end, int)
            or start < 1
            or end < start
        ):
            return {
                "status": "error",
                "error": "start and end are required integers with 1 <= start <= end "
                "(GRCh37/hg19).",
            }
        if end - start > MAX_REGION_BP:
            return {
                "status": "error",
                "error": f"The window is {end - start:,} bp; EWAS Atlas times out "
                f"above about {MAX_REGION_BP:,} bp. Split the region.",
            }
        payload = self._fetch("pos", {"chr": chromosome, "start": start, "end": end})
        raw_probes = payload.get("data") if payload.get("code") == 0 else None
        query = {"chromosome": chromosome, "start": start, "end": end}
        if not raw_probes:
            return {
                "status": "success",
                "data": [],
                "metadata": {
                    **query,
                    "source": "EWAS Atlas (NGDC)",
                    "total_probes": 0,
                    "note": "No EWAS Atlas probes in this window. Coordinates "
                    "are GRCh37/hg19.",
                },
            }
        return self._probe_list(raw_probes, arguments, query)

    def _get_study(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        study_id, error = self._required(arguments, "study_id", "ES00033")
        if error:
            return error
        payload = self._fetch("study", {"studyId": study_id})
        raw = payload.get("data")
        if payload.get("code") != 0 or not isinstance(raw, dict):
            return {
                "status": "error",
                "error": f"EWAS Atlas has no study '{study_id}': {payload.get('msg')}",
            }
        study = _study(raw, _limit(arguments.get("limit"), 100, 1000))
        return {
            "status": "success",
            "data": study,
            "metadata": {
                "source": "EWAS Atlas (NGDC)",
                "returned_associations": len(study["associations"]),
            },
        }

    def _get_publication(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        pmid, error = self._required(arguments, "pmid", "29535343")
        if error:
            return error
        payload = self._fetch("publication", {"pmid": pmid})
        raw = payload.get("data")
        if payload.get("code") != 0 or not isinstance(raw, dict):
            return {
                "status": "error",
                "error": f"EWAS Atlas has no publication with PMID {pmid}: "
                f"{payload.get('msg')}",
            }
        per_study = _limit(arguments.get("limit"), 50, 1000)
        studies = [
            _study(s, per_study)
            for s in raw.get("studyList") or []
            if isinstance(s, dict)
        ]
        return {
            "status": "success",
            "data": {
                "pmid": str(raw.get("pmid")) if raw.get("pmid") is not None else pmid,
                "title": raw.get("title"),
                "doi": raw.get("doi") or None,
                "publication_date": raw.get("publicationDate"),
                "studies": studies,
            },
            "metadata": {
                "source": "EWAS Atlas (NGDC)",
                "study_count": len(studies),
            },
        }
