# clingen_ar_tool.py
"""
ClinGen Allele Registry API tool for ToolUniverse.

The ClinGen Allele Registry provides canonical identifiers (CA IDs) for
genetic variants, normalizing representations across different nomenclatures
and coordinate systems. It links to ClinVar, dbSNP, COSMIC, gnomAD, and
other variant databases.

API: https://reg.clinicalgenome.org/
No authentication required. Free public access.
"""

import re

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

CLINGEN_AR_BASE_URL = "https://reg.clinicalgenome.org"

# A registry allele carries one transcript allele per Ensembl/RefSeq transcript
# of every overlapping gene: BRAF c.1799T>A has 48. They are returned in full up
# to this cap, with the MANE Select one surfaced separately whatever its
# position, and the count and the cut disclosed.
TRANSCRIPTS_PER_ALLELE = 25

# Each external database names its identifier differently, and `id` is absent on
# several: dbSNP sends `rs`, ClinVar alleles send `alleleId`, ClinVar variations
# send `variationId`. Reading `id` alone returned None for them.
_ID_KEYS = ("rs", "alleleId", "variationId", "accession", "variant")


def _snake(key: str) -> str:
    """`alleleId` -> `allele_id`, `RCV` -> `rcv`, `@id` -> `id`."""
    key = key.lstrip("@")
    key = re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", key)
    return key.lower()


def _coordinates(node: Dict[str, Any]) -> list:
    """Where the allele sits and what it replaces, in this representation.

    For an intronic variant the registry gives the position as an exon
    boundary plus an offset into the intron: 6 of BRAF c.1799T>A's 48
    transcript alleles read start 1258 with startIntronOffset 3918 in the
    '-' direction, i.e. 1258-3918. Reporting the 1258 alone does not omit a
    field, it names a different position.
    """
    out = []
    for coord in node.get("coordinates") or []:
        if not isinstance(coord, dict):
            continue
        row = {
            "start": coord.get("start"),
            "end": coord.get("end"),
            "reference_allele": coord.get("referenceAllele"),
            "allele": coord.get("allele"),
            "start_intron_offset": coord.get("startIntronOffset"),
            "start_intron_direction": coord.get("startIntronDirection"),
            "end_intron_offset": coord.get("endIntronOffset"),
            "end_intron_direction": coord.get("endIntronDirection"),
        }
        row["is_intronic"] = (
            row["start_intron_offset"] is not None
            or row["end_intron_offset"] is not None
        )
        out.append(row)
    return out


def _genomic_allele(ga: Dict[str, Any]) -> Dict[str, Any]:
    """One assembly's representation: every HGVS spelling, not just the first."""
    hgvs = [h for h in (ga.get("hgvs") or []) if h]
    return {
        "hgvs": hgvs[0] if hgvs else None,
        "hgvs_all": hgvs,
        "reference_genome": ga.get("referenceGenome"),
        "chromosome": ga.get("chromosome"),
        "coordinates": _coordinates(ga),
        "reference_sequence": ga.get("referenceSequence"),
    }


def _transcript_allele(ta: Dict[str, Any]) -> Dict[str, Any]:
    """One transcript's representation: the gene, the c. and the p. change."""
    hgvs = [h for h in (ta.get("hgvs") or []) if h]
    protein = ta.get("proteinEffect") or {}
    mane = ta.get("MANE") or {}
    nucleotide = mane.get("nucleotide") or {}
    mane_protein = mane.get("protein") or {}
    return {
        "hgvs": hgvs[0] if hgvs else None,
        "hgvs_all": hgvs,
        "gene_symbol": ta.get("geneSymbol"),
        "gene_ncbi_id": ta.get("geneNCBI_id"),
        "gene_url": ta.get("gene"),
        "protein_hgvs": protein.get("hgvs"),
        "protein_hgvs_well_defined": protein.get("hgvsWellDefined"),
        "coordinates": _coordinates(ta),
        "reference_sequence": ta.get("referenceSequence"),
        "mane_status": mane.get("maneStatus"),
        "mane_version": mane.get("maneVersion"),
        "mane_refseq_hgvs": (nucleotide.get("RefSeq") or {}).get("hgvs"),
        "mane_ensembl_hgvs": (nucleotide.get("Ensembl") or {}).get("hgvs"),
        "mane_refseq_protein_hgvs": (mane_protein.get("RefSeq") or {}).get("hgvs"),
        "mane_ensembl_protein_hgvs": (mane_protein.get("Ensembl") or {}).get("hgvs"),
    }


def _transcript_summary(data: Dict[str, Any]) -> Dict[str, Any]:
    """The gene and protein change the registry states, plus the transcripts.

    The tool's own description promises 'CA000387 (TP53 p.Arg248Gln)', and
    neither the gene symbol nor the protein effect was being read: both live
    only on `transcriptAlleles`, which the wrapper never looked at.
    """
    rows = [
        _transcript_allele(ta)
        for ta in (data.get("transcriptAlleles") or [])
        if isinstance(ta, dict)
    ]
    genes = sorted({row["gene_symbol"] for row in rows if row["gene_symbol"]})
    mane = next((row for row in rows if row.get("mane_status")), None)
    preferred = mane or (rows[0] if rows else None)
    return {
        "gene_symbol": genes[0] if len(genes) == 1 else None,
        "gene_symbols": genes,
        "gene_ncbi_id": next(
            (row["gene_ncbi_id"] for row in rows if row.get("gene_ncbi_id")), None
        ),
        "protein_effect": (preferred or {}).get("protein_hgvs"),
        "mane_select_transcript": mane,
        "transcript_allele_count": len(rows),
        "transcript_alleles": rows[:TRANSCRIPTS_PER_ALLELE],
        "transcript_alleles_truncated": len(rows) > TRANSCRIPTS_PER_ALLELE,
    }


def _external_record(rec: Any) -> Dict[str, Any]:
    """One database's record, with every key it sent and an id under some name."""
    if not isinstance(rec, dict):
        return {"id": rec, "url": None}
    out: Dict[str, Any] = {"url": rec.get("@id")}
    for key, value in rec.items():
        if key == "@id":
            continue
        out[_snake(key)] = value
    if out.get("id") is None:
        for key in _ID_KEYS:
            if rec.get(key) is not None:
                out["id"] = (
                    f"rs{rec[key]}" if key == "rs" else str(rec[key])
                )
                break
    return out


@register_tool("ClinGenARTool")
class ClinGenARTool(BaseTool):
    """
    Tool for querying the ClinGen Allele Registry.

    The Allele Registry normalizes variant nomenclature and provides
    canonical allele identifiers (CA IDs) that link to ClinVar, dbSNP,
    COSMIC, gnomAD, and other variant databases. Supports HGVS notation
    lookup and external record retrieval.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "lookup_allele")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the ClinGen Allele Registry API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"ClinGen AR API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to ClinGen Allele Registry",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"ClinGen AR API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying ClinGen AR: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate ClinGen AR endpoint."""
        if self.endpoint == "lookup_allele":
            return self._lookup_allele(arguments)
        elif self.endpoint == "get_external_records":
            return self._get_external_records(arguments)
        elif self.endpoint == "lookup_by_external_id":
            return self._lookup_by_external_id(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    def _lookup_allele(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Look up a variant by HGVS notation."""
        hgvs = arguments.get("hgvs", "")
        if not hgvs:
            return {"status": "error", "error": "hgvs parameter is required"}

        url = f"{CLINGEN_AR_BASE_URL}/allele"
        params = {"hgvs": hgvs}
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()

        # Extract allele ID from @id URL
        allele_url = data.get("@id", "")
        allele_id = allele_url.split("/")[-1] if allele_url else None

        # Extract community standard title
        titles = data.get("communityStandardTitle", [])
        title = titles[0] if titles else None

        # Extract external records summary
        external_records = data.get("externalRecords", {})

        # Extract genomic alleles
        genomic_alleles = [
            _genomic_allele(ga)
            for ga in data.get("genomicAlleles", [])
            if isinstance(ga, dict)
        ]

        return {
            "status": "success",
            "data": {
                "allele_id": allele_id,
                "allele_url": allele_url,
                "community_standard_title": title,
                "allele_type": data.get("type"),
                "community_standard_titles": list(titles or []),
                "external_records": external_records,
                "genomic_alleles": genomic_alleles,
                **_transcript_summary(data),
            },
            "metadata": {
                "source": "ClinGen Allele Registry",
                "query_hgvs": hgvs,
            },
        }

    def _get_external_records(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get external database records for a canonical allele ID."""
        allele_id = arguments.get("allele_id", "")
        if not allele_id:
            return {"status": "error", "error": "allele_id parameter is required"}

        url = f"{CLINGEN_AR_BASE_URL}/allele/{allele_id}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()

        # Extract community standard title
        titles = data.get("communityStandardTitle", [])
        title = titles[0] if titles else None

        # Extract external records
        external_records = data.get("externalRecords", {})

        # Build database summary. `id` is not the identifier key every database
        # uses -- dbSNP sends `rs`, ClinVar alleles `alleleId` -- so reading it
        # alone handed back `{"id": None}` for them, and dropped the ClinVar
        # preferred name, the RCV accessions and the gnomAD/ExAC variant string.
        databases = {}
        for db_name, records in external_records.items():
            if isinstance(records, list):
                databases[db_name] = [_external_record(rec) for rec in records]

        return {
            "status": "success",
            "data": {
                "allele_id": allele_id,
                "community_standard_title": title,
                "databases": databases,
                "database_count": len(databases),
                "record_count": sum(len(rows) for rows in databases.values()),
                **_transcript_summary(data),
            },
            "metadata": {
                "source": "ClinGen Allele Registry",
                "query_allele_id": allele_id,
            },
        }

    def _lookup_by_external_id(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Reverse-resolve a dbSNP rsID or ClinVar variation id to the canonical allele.

        Queries ``GET /alleles?dbSNP.rs=<n>`` or ``?ClinVar.variationId=<n>`` and
        returns the canonical allele (CA id) plus all cross-references. The
        ``/alleles`` endpoint returns a JSON array (one record per matching allele).
        """
        rs = arguments.get("dbsnp_rs")
        if rs in (None, ""):
            rs = arguments.get("rs")
        clinvar_variation_id = arguments.get("clinvar_variation_id")
        if clinvar_variation_id in (None, ""):
            clinvar_variation_id = arguments.get("variation_id")

        if rs not in (None, ""):
            query_key = "dbSNP.rs"
            query_value = str(rs).lower().lstrip("rs") or str(rs)
            query_label = f"dbSNP.rs={query_value}"
        elif clinvar_variation_id not in (None, ""):
            query_key = "ClinVar.variationId"
            query_value = str(clinvar_variation_id)
            query_label = f"ClinVar.variationId={query_value}"
        else:
            return {
                "status": "error",
                "error": "Provide either dbsnp_rs (a dbSNP rsID, e.g. 113488022) "
                "or clinvar_variation_id (a ClinVar VariationID, e.g. 13961).",
            }

        url = f"{CLINGEN_AR_BASE_URL}/alleles"
        params = {query_key: query_value}
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()

        records = response.json()
        if not isinstance(records, list):
            records = [records] if records else []
        if not records:
            return {
                "status": "error",
                "error": f"No ClinGen allele found for {query_label}.",
            }

        alleles = []
        for rec in records:
            allele_url = rec.get("@id", "")
            allele_id = allele_url.split("/")[-1] if allele_url else None
            titles = rec.get("communityStandardTitle", [])
            title = titles[0] if titles else None
            alleles.append(
                {
                    "allele_id": allele_id,
                    "allele_url": allele_url,
                    "community_standard_title": title,
                    "allele_type": rec.get("type"),
                    "external_records": rec.get("externalRecords", {}),
                    "genomic_alleles": [
                        _genomic_allele(ga)
                        for ga in rec.get("genomicAlleles", [])
                        if isinstance(ga, dict)
                    ],
                    **_transcript_summary(rec),
                }
            )

        return {
            "status": "success",
            "data": {
                "query": query_label,
                "allele_count": len(alleles),
                "alleles": alleles,
            },
            "metadata": {
                "source": "ClinGen Allele Registry",
                "query": query_label,
            },
        }
