"""
MaveDB Tool - Multiplexed Assay of Variant Effect Database

MaveDB stores and distributes results from Multiplexed Assays of Variant Effect
(MAVEs), including deep mutational scanning experiments. Score sets contain
functional impact scores for thousands of variants in a single protein/gene.

API: https://api.mavedb.org/api/v1/
Reference: Esposito et al. (2019) Genome Research
"""

import csv
import io
import re
from collections import Counter

import requests
from typing import Dict, Any, List, Optional, Tuple
from .base_tool import BaseTool
from .tool_registry import register_tool

MAVEDB_API = "https://api.mavedb.org/api/v1"
UNIPROT_API = "https://rest.uniprot.org/uniprotkb"

# Standard 20-amino-acid order (matches what every downstream skill expects)
_STANDARD_AAS = "ACDEFGHIKLMNPQRSTVWY"
_THREE_TO_ONE: Dict[str, str] = {
    "Ala": "A",
    "Arg": "R",
    "Asn": "N",
    "Asp": "D",
    "Cys": "C",
    "Gln": "Q",
    "Glu": "E",
    "Gly": "G",
    "His": "H",
    "Ile": "I",
    "Leu": "L",
    "Lys": "K",
    "Met": "M",
    "Phe": "F",
    "Pro": "P",
    "Ser": "S",
    "Thr": "T",
    "Trp": "W",
    "Tyr": "Y",
    "Val": "V",
}
_HGVS_SINGLE_MISSENSE_RE = re.compile(r"^p\.\(?([A-Z][a-z]{2})(\d+)([A-Z][a-z]{2})\)?$")


@register_tool("MaveDBTool")
class MaveDBTool(BaseTool):
    """Search MaveDB for variant effect score sets and retrieve details."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    def _search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search MaveDB score sets by text query."""
        query = params.get("query", "")
        limit = params.get("limit", 20)
        if not query:
            return {"status": "error", "error": "query parameter is required"}

        resp = self.session.post(
            f"{MAVEDB_API}/score-sets/search",
            json={"text": query},
            timeout=30,
        )
        if resp.status_code != 200:
            return {
                "status": "error",
                "error": f"MaveDB search failed: HTTP {resp.status_code}",
            }

        data = resp.json()
        score_sets = data.get("scoreSets", [])[:limit]
        results = []
        for ss in score_sets:
            results.append(
                {
                    "urn": ss.get("urn"),
                    "title": ss.get("title"),
                    "short_description": ss.get("shortDescription"),
                    "num_variants": ss.get("numVariants"),
                    "published_date": ss.get("publishedDate"),
                }
            )
        return {
            "status": "success",
            "data": results,
            "metadata": {
                "total_results": len(score_sets),
                "query": query,
            },
        }

    def _get_score_set(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed information about a specific score set by URN."""
        urn = params.get("urn", "")
        if not urn:
            return {"status": "error", "error": "urn parameter is required"}

        resp = self.session.get(f"{MAVEDB_API}/score-sets/{urn}", timeout=30)
        if resp.status_code == 404:
            return {
                "status": "error",
                "error": f"Score set '{urn}' not found in MaveDB",
            }
        if resp.status_code != 200:
            return {
                "status": "error",
                "error": f"MaveDB request failed: HTTP {resp.status_code}",
            }

        d = resp.json()
        target_genes = []
        for tg in d.get("targetGenes") or []:
            gene_info = {
                "name": tg.get("name"),
                "category": tg.get("category"),
            }
            ref = tg.get("targetSequence") or {}
            gene_info["uniprot_id"] = (
                ref.get("uniprot", {}).get("identifier") if ref.get("uniprot") else None
            )
            target_genes.append(gene_info)

        result = {
            "urn": d.get("urn"),
            "title": d.get("title"),
            "short_description": d.get("shortDescription"),
            "abstract": d.get("abstractText"),
            "method": d.get("methodText"),
            "num_variants": d.get("numVariants"),
            "published_date": d.get("publishedDate"),
            "license": (
                d.get("license", {}).get("shortName") if d.get("license") else None
            ),
            "target_genes": target_genes,
            "doi_identifiers": [
                doi.get("identifier") for doi in d.get("doiIdentifiers") or []
            ],
            "primary_publications": [
                pub.get("identifier")
                for pub in d.get("primaryPublicationIdentifiers") or []
            ],
        }
        return {
            "status": "success",
            "data": result,
            "metadata": {"urn": urn},
        }

    def _get_variant_scores(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get variant functional scores from a score set (CSV endpoint)."""
        urn = params.get("urn", "")
        if not urn:
            return {"status": "error", "error": "urn parameter is required"}

        hgvs_filter = (params.get("hgvs_pro") or "").strip()
        # limit semantics: client-side truncation of the CSV returned by the
        # /scores endpoint (the endpoint itself returns every variant in one
        # call — there is no server-side pagination). limit=None / omitted /
        # 0 means "return all", which is what DMS workflows need on whole-
        # protein score sets (e.g. KRAS folding ΔΔG has ~2200 variants).
        raw_limit = params.get("limit")
        limit = None
        if raw_limit is not None:
            try:
                lv = int(raw_limit)
                limit = None if lv <= 0 else lv
            except (TypeError, ValueError):
                limit = None

        try:
            resp = self.session.get(
                f"{MAVEDB_API}/score-sets/{urn}/scores",
                timeout=60,
                headers={"Accept": "text/csv"},
            )
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"MaveDB API error: {e}"}

        if resp.status_code == 404:
            return {
                "status": "error",
                "error": f"Score set '{urn}' not found in MaveDB",
            }
        if resp.status_code != 200:
            return {
                "status": "error",
                "error": f"MaveDB request failed: HTTP {resp.status_code}",
            }

        csv_text = resp.text
        if not csv_text.strip():
            return {
                "status": "error",
                "error": f"No scores available for '{urn}'",
            }

        reader = csv.DictReader(io.StringIO(csv_text))
        variants = []
        total_parsed = 0
        for row in reader:
            total_parsed += 1
            if hgvs_filter:
                hgvs_pro_val = row.get("hgvs_pro") or ""
                if hgvs_filter.lower() not in hgvs_pro_val.lower():
                    continue

            variant = {
                "hgvs_nt": row.get("hgvs_nt") or None,
                "hgvs_splice": row.get("hgvs_splice") or None,
                "hgvs_pro": row.get("hgvs_pro") or None,
            }
            for key, value in row.items():
                if key in ("accession", "hgvs_nt", "hgvs_splice", "hgvs_pro"):
                    continue
                if value and value != "NA":
                    try:
                        variant[key] = float(value)
                    except ValueError:
                        variant[key] = value

            variants.append(variant)
            if limit is not None and len(variants) >= limit:
                # Continue counting total_parsed so we can report the true total
                # in the response (let the user know more variants exist that
                # were truncated client-side).
                for _ in reader:
                    total_parsed += 1
                break

        truncated = (
            limit is not None and len(variants) >= limit and total_parsed > limit
        )
        return {
            "status": "success",
            "data": {
                "urn": urn,
                "total_variants_in_set": total_parsed,
                "returned": len(variants),
                "truncated": truncated,
                "limit_applied": limit,
                "hgvs_filter": hgvs_filter or None,
                "variants": variants,
            },
        }

    def _search_experiments(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search MaveDB experiments by text query."""
        query = params.get("query", "")
        if not query:
            return {"status": "error", "error": "query parameter is required"}

        try:
            resp = self.session.post(
                f"{MAVEDB_API}/experiments/search",
                json={"text": query},
                timeout=30,
            )
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"MaveDB API error: {e}"}

        if resp.status_code != 200:
            return {
                "status": "error",
                "error": f"MaveDB search failed: HTTP {resp.status_code}",
            }

        raw = resp.json()
        if not isinstance(raw, list):
            raw = [raw] if raw else []

        experiments = []
        for exp in raw:
            urn = exp.get("urn", "")
            if urn.startswith("tmp:"):
                continue

            pubs = [
                {
                    "identifier": pub.get("identifier"),
                    "db_name": pub.get("dbName"),
                    "title": pub.get("title"),
                }
                for pub in exp.get("primaryPublicationIdentifiers") or []
            ]
            score_set_urns = exp.get("scoreSetUrns") or []
            experiments.append(
                {
                    "urn": urn,
                    "title": exp.get("title"),
                    "short_description": exp.get("shortDescription"),
                    "published_date": exp.get("publishedDate"),
                    "score_set_urns": score_set_urns,
                    "num_score_sets": len(score_set_urns),
                    "publications": pubs,
                }
            )

        return {
            "status": "success",
            "data": {
                "query": query,
                "total_experiments": len(experiments),
                "experiments": experiments,
            },
        }

    def _get_effect_matrix(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch DMS score set and return ready-to-analyze effect matrix.

        Hides the parsing pipeline that every consuming skill used to inline:
          1. Fetch all variants (uses _get_variant_scores with no limit)
          2. Parse HGVS protein notation → (ref_aa, position, alt_aa)
          3. Filter to single missense (drop synonymous/nonsense/indels/multi)
          4. Optional: verify position numbering against UniProt canonical
          5. Reshape to (20 amino acids × n_positions) matrix in standard
             AA order ('ACDEFGHIKLMNPQRSTVWY')
        """
        urn = params.get("urn", "")
        if not urn:
            return {"status": "error", "error": "urn parameter is required"}

        uniprot_id: Optional[str] = params.get("uniprot_id")
        score_field: Optional[str] = params.get("score_field")

        # 1) Pull all variants via the existing helper (it uses the same session)
        raw = self._get_variant_scores({"urn": urn, "limit": 0})
        if raw.get("status") != "success":
            return raw

        variants = raw["data"].get("variants", [])
        total_in_set = raw["data"].get("total_variants_in_set", len(variants))

        # 2-3) parse HGVS + filter to single missense
        parsed: List[Tuple[str, int, str, float]] = []
        n_dropped = 0
        score_field_counter: Counter = Counter()
        for row in variants:
            hgvs = row.get("hgvs_pro") or ""
            m = _HGVS_SINGLE_MISSENSE_RE.match(hgvs)
            if not m:
                n_dropped += 1
                continue
            ref3, pos_str, alt3 = m.group(1), m.group(2), m.group(3)
            if ref3 not in _THREE_TO_ONE or alt3 not in _THREE_TO_ONE:
                n_dropped += 1
                continue
            # Pick a score field — explicit > 'score' > 'ddG' > 'fitness' > first numeric
            score: Optional[float] = None
            if score_field and score_field in row:
                try:
                    score = float(row[score_field])
                    score_field_counter[score_field] += 1
                except (TypeError, ValueError):
                    pass
            else:
                for cand in ("score", "ddG", "fitness"):
                    if row.get(cand) is None:
                        continue
                    try:
                        score = float(row[cand])
                        score_field_counter[cand] += 1
                        break
                    except (TypeError, ValueError):
                        continue
                if score is None:
                    for k, v in row.items():
                        if k.startswith("hgvs") or k == "accession":
                            continue
                        try:
                            score = float(v)
                            score_field_counter[k] += 1
                            break
                        except (TypeError, ValueError):
                            continue
            if score is None or (isinstance(score, float) and (score != score)):
                n_dropped += 1
                continue
            parsed.append(
                (_THREE_TO_ONE[ref3], int(pos_str), _THREE_TO_ONE[alt3], score)
            )

        if not parsed:
            return {
                "status": "error",
                "error": (
                    f"No usable single-missense variants found in '{urn}' "
                    f"({total_in_set} rows, {n_dropped} dropped — check that the "
                    f"score set uses HGVS protein notation and has numeric scores)."
                ),
            }

        score_field_used = (
            score_field_counter.most_common(1)[0][0] if score_field_counter else None
        )

        # 4) optional numbering verification against UniProt canonical
        numbering_offset: Optional[int] = None
        landmark_check: Optional[Dict[str, Any]] = None
        if uniprot_id:
            try:
                resp = self.session.get(f"{UNIPROT_API}/{uniprot_id}.fasta", timeout=30)
                if resp.status_code == 200:
                    seq_lines = resp.text.strip().splitlines()
                    canonical_seq = "".join(seq_lines[1:])
                    # Use the most-common parsed position as the landmark
                    position_counts = Counter(p[1] for p in parsed)
                    landmark_pos = position_counts.most_common(1)[0][0]
                    landmark_ref = next(p[0] for p in parsed if p[1] == landmark_pos)
                    seq_idx = landmark_pos - 1
                    if 0 <= seq_idx < len(canonical_seq):
                        uniprot_aa = canonical_seq[seq_idx]
                        if uniprot_aa == landmark_ref:
                            numbering_offset = 0
                            landmark_check = {
                                "position": landmark_pos,
                                "mavedb_ref": landmark_ref,
                                "uniprot_aa": uniprot_aa,
                                "match": True,
                            }
                        else:
                            # Try common offsets to detect the shift
                            offset_detected = None
                            for offset in range(-10, 11):
                                target_idx = seq_idx + offset
                                if (
                                    0 <= target_idx < len(canonical_seq)
                                    and canonical_seq[target_idx] == landmark_ref
                                ):
                                    offset_detected = offset
                                    break
                            landmark_check = {
                                "position": landmark_pos,
                                "mavedb_ref": landmark_ref,
                                "uniprot_aa": uniprot_aa,
                                "match": False,
                                "detected_offset": offset_detected,
                                "warning": (
                                    f"MaveDB position {landmark_pos} has ref_aa "
                                    f"{landmark_ref} but UniProt {uniprot_id} "
                                    f"position {landmark_pos} is {uniprot_aa}."
                                    + (
                                        f" Likely offset = {offset_detected}."
                                        if offset_detected is not None
                                        else ""
                                    )
                                ),
                            }
                            numbering_offset = offset_detected
                else:
                    landmark_check = {
                        "warning": f"UniProt {uniprot_id} lookup HTTP {resp.status_code}"
                    }
            except requests.exceptions.RequestException as exc:
                landmark_check = {"warning": f"UniProt verification failed: {exc}"}

        # 5) reshape into (20 × n_positions)
        positions = sorted({p[1] for p in parsed})
        pos_index = {p: i for i, p in enumerate(positions)}
        aa_index = {a: i for i, a in enumerate(_STANDARD_AAS)}

        matrix: List[List[Optional[float]]] = [
            [None] * len(positions) for _ in range(20)
        ]
        for ref_aa, pos, alt_aa, score in parsed:
            if alt_aa not in aa_index:
                continue
            matrix[aa_index[alt_aa]][pos_index[pos]] = score

        return {
            "status": "success",
            "data": {
                "urn": urn,
                "matrix": matrix,
                "positions": positions,
                "amino_acid_order": _STANDARD_AAS,
                "shape": [20, len(positions)],
                "n_parsed_single_missense": len(parsed),
                "n_dropped": n_dropped,
                "n_total_rows": total_in_set,
                "score_field_used": score_field_used,
                "numbering_check": landmark_check,
                "numbering_offset": numbering_offset,
            },
            "metadata": {
                "source": "MaveDB",
                "matrix_layout": (
                    "rows = 20 amino acids in 'ACDEFGHIKLMNPQRSTVWY' order; "
                    "columns = positions (1-based canonical, see positions field); "
                    "cells = score (None for unmeasured / WT-diagonal)"
                ),
                "note": (
                    "WT diagonal cells are None (the MaveDB API doesn't "
                    "include 'X→X' rows). Downstream skills should treat None "
                    "as missing data."
                ),
            },
        }

    def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        operation = self.tool_config.get("fields", {}).get("operation", "")
        dispatch = {
            "search": self._search,
            "get_score_set": self._get_score_set,
            "get_variant_scores": self._get_variant_scores,
            "search_experiments": self._search_experiments,
            "get_effect_matrix": self._get_effect_matrix,
        }
        handler = dispatch.get(operation)
        if handler:
            return handler(params)
        return {"status": "error", "error": f"Unknown operation: {operation}"}
