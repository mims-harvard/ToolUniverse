# mygene_tool.py
"""
MyGene.info API tool for ToolUniverse.

MyGene.info is a high-performance gene annotation service providing
access to gene information from 30+ sources for 22M+ genes across 22K+ species.

API Documentation: https://mygene.info/doc
"""

import re
import requests
from typing import Dict, Any, Optional, List
from .base_tool import BaseTool
from .tool_registry import register_tool

# Base URL for MyGene.info API v3
MYGENE_BASE_URL = "https://mygene.info/v3"

# An rsID resolves in either assembly and to any number of records; an HGVS id
# does neither. Several MyVariant behaviours below fork on this distinction.
RSID_PATTERN = re.compile(r"^rs\d+$", re.IGNORECASE)


@register_tool("MyGeneTool")
class MyGeneTool(BaseTool):
    """
    Tool for querying MyGene.info API.

    MyGene.info provides gene annotation data from 30+ sources including
    Entrez Gene, Ensembl, UniProt, HGNC, and more.

    No authentication required. Free for academic/research use.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        # Get the operation type from config
        self.operation = tool_config.get("fields", {}).get("operation", "query")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the MyGene.info API call."""
        operation = self.operation

        if operation == "query":
            return self._query_genes(arguments)
        elif operation == "get_gene":
            return self._get_gene(arguments)
        elif operation == "query_batch":
            return self._query_batch(arguments)
        else:
            return {"status": "error", "error": f"Unknown operation: {operation}"}

    def _query_genes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Query genes by keyword, symbol, or other identifiers.

        Endpoint: GET /query
        """
        query = arguments.get("query", "")
        species = arguments.get("species", "human")
        fields = arguments.get("fields", "symbol,name,entrezgene,ensembl.gene")
        size = arguments.get("size", 10)

        if not query:
            return {"status": "error", "error": "Query parameter is required"}

        params = {
            "q": query,
            "species": species,
            "fields": fields,
            "size": min(size, 100),  # Cap at 100 to avoid overwhelming responses
        }

        try:
            response = requests.get(
                f"{MYGENE_BASE_URL}/query", params=params, timeout=self.timeout
            )
            response.raise_for_status()
            return {"status": "success", "data": response.json()}
        except requests.RequestException as e:
            return {
                "status": "error",
                "error": f"MyGene.info API request failed: {str(e)}",
            }

    def _get_gene(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get detailed gene annotation by gene ID.

        Endpoint: GET /gene/<geneid>
        """
        gene_id = arguments.get("gene_id", "")
        fields = arguments.get(
            "fields", "symbol,name,entrezgene,ensembl,summary,generif,pathway"
        )

        if not gene_id:
            return {"status": "error", "error": "gene_id parameter is required"}

        params = {"fields": fields}

        try:
            response = requests.get(
                f"{MYGENE_BASE_URL}/gene/{gene_id}", params=params, timeout=self.timeout
            )
            response.raise_for_status()
            return {"status": "success", "data": response.json()}
        except requests.RequestException as e:
            return {
                "status": "error",
                "error": f"MyGene.info API request failed: {str(e)}",
            }

    def _query_batch(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Query multiple genes at once using POST.

        Endpoint: POST /query
        """
        gene_ids = arguments.get("gene_ids", [])
        fields = arguments.get("fields", "symbol,name,entrezgene")
        species = arguments.get("species", "human")

        if not gene_ids:
            return {
                "status": "error",
                "error": "gene_ids parameter is required (list of gene IDs)",
            }

        # Convert list to comma-separated string if needed
        if isinstance(gene_ids, list):
            gene_ids_str = ",".join(str(g) for g in gene_ids)
        else:
            gene_ids_str = str(gene_ids)

        data = {
            "q": gene_ids_str,
            "scopes": "entrezgene,ensembl.gene,symbol",
            "species": species,
            "fields": fields,
        }

        try:
            response = requests.post(
                f"{MYGENE_BASE_URL}/query", data=data, timeout=self.timeout
            )
            response.raise_for_status()
            return {"status": "success", "data": {"results": response.json()}}
        except requests.RequestException as e:
            return {
                "status": "error",
                "error": f"MyGene.info API request failed: {str(e)}",
            }


@register_tool("MyVariantTool")
class MyVariantTool(BaseTool):
    """
    Tool for querying MyVariant.info API.

    MyVariant.info provides variant annotation data from 19+ sources
    for 400M+ human variants.

    No authentication required. Free for academic/research use.
    """

    MYVARIANT_BASE_URL = "https://myvariant.info/v1"

    # MyVariant.info serves every genomic coordinate in a reference assembly
    # that its payload never names, and the one it defaults to is GRCh37/hg19:
    # rs4244285 comes back as chr10:g.96541616G>C, about 1.76 Mb from the
    # chr10:g.94781859G>C that Ensembl and gnomAD report for the same variant on
    # GRCh38. An unlabelled coordinate is exactly the value that ends up pasted
    # into a report beside a GRCh38 one, so every response now carries
    # `coordinate_assembly`, spelling out both nomenclatures because clinicians
    # read "GRCh37" where pipelines write "hg19". The default stays "hg19" so
    # callers who never pass `assembly` get precisely the frame they got before.
    # The label sits beside `status`/`data` rather than inside `data`, because
    # `data` is MyVariant's own payload and must stay untouched -- and for
    # /variant/<rsid> it is sometimes a list, with nowhere to put a key at all.
    ASSEMBLY_LABELS = {"hg19": "hg19 (GRCh37)", "hg38": "hg38 (GRCh38)"}

    # Field roots that locate or identify a variant rather than annotate it. A
    # record carrying only these is a stub, which is the state
    # _sibling_annotation_records cross-checks. Missing a root from this list
    # only costs the bonus lookup -- the primary answer is unaffected either
    # way -- so it is deliberately a short list of the common locator fields
    # rather than an exhaustive one.
    IDENTITY_FIELD_ROOTS = frozenset(
        {
            "_id",
            "_score",
            "_version",
            "_license",
            "dbsnp",
            "chrom",
            "vcf",
            "hg19",
            "hg38",
            "observed",
        }
    )

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.operation = tool_config.get("fields", {}).get("operation", "query")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the MyVariant.info API call."""
        operation = self.operation

        if operation == "query":
            return self._query_variants(arguments)
        elif operation == "get_variant":
            return self._get_variant(arguments)
        else:
            return {"status": "error", "error": f"Unknown operation: {operation}"}

    def _resolve_assembly(self, arguments: Dict[str, Any]):
        """Validate the `assembly` argument; returns ``(assembly, error)``."""
        assembly = str(arguments.get("assembly") or "hg19").strip().lower()
        if assembly not in self.ASSEMBLY_LABELS:
            return None, {
                "status": "error",
                "error": (
                    f"Unknown assembly '{assembly}'. Supported assemblies: "
                    f"{', '.join(sorted(self.ASSEMBLY_LABELS))}."
                ),
            }
        return assembly, None

    @staticmethod
    def _assembly_params(assembly: str) -> Dict[str, str]:
        """Upstream query parameters selecting `assembly`.

        Empty for hg19: MyVariant already treats a missing `assembly` as hg19,
        so omitting it keeps the default request -- and therefore the default
        response -- byte-identical to what it was before this parameter existed.
        """
        return {} if assembly == "hg19" else {"assembly": assembly}

    def _query_variants(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Query variants by various criteria.

        Endpoint: GET /query
        """
        query = arguments.get("query", "")
        fields = arguments.get("fields", "dbsnp,clinvar,cadd,gnomad_genome")
        size = arguments.get("size", 10)

        if not query:
            return {"status": "error", "error": "Query parameter is required"}

        assembly, error = self._resolve_assembly(arguments)
        if error:
            return error

        params = {"q": query, "fields": fields, "size": min(size, 100)}
        params.update(self._assembly_params(assembly))
        label = self.ASSEMBLY_LABELS[assembly]
        try:
            response = requests.get(
                f"{self.MYVARIANT_BASE_URL}/query", params=params, timeout=self.timeout
            )
            response.raise_for_status()
            return {
                "status": "success",
                "coordinate_assembly": label,
                "data": response.json(),
            }
        except requests.RequestException as e:
            return {
                "status": "error",
                "coordinate_assembly": label,
                "error": f"MyVariant.info API request failed: {str(e)}",
            }

    def _declared_fields_default(self) -> str:
        """The `fields` default this tool instance declares in its schema.

        This handler backs both MyVariant_get_variant_annotation and
        MyVariant_get_pathogenicity_scores (both operation="get_variant").
        Read the per-instance declared default instead of hardcoding the
        generic annotation field list for both, or
        MyVariant_get_pathogenicity_scores (whose schema declares a curated
        list of dbnsfp pathogenicity-prediction fields) silently returns
        generic annotation data instead whenever `fields` is omitted.
        """
        return (
            self.tool_config.get("parameter", {})
            .get("properties", {})
            .get("fields", {})
            .get("default", "dbsnp,clinvar,cadd,gnomad_genome,dbnsfp")
        )

    def _get_variant(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get detailed variant annotation by HGVS ID.

        Endpoint: GET /variant/<hgvsid>
        """
        variant_id = arguments.get("variant_id", "")
        fields = arguments.get("fields", self._declared_fields_default())

        if not variant_id:
            return {
                "status": "error",
                "error": "variant_id parameter is required (HGVS format)",
            }

        assembly, error = self._resolve_assembly(arguments)
        if error:
            return error

        params = {"fields": fields}
        params.update(self._assembly_params(assembly))
        label = self.ASSEMBLY_LABELS[assembly]

        try:
            response = requests.get(
                f"{self.MYVARIANT_BASE_URL}/variant/{variant_id}",
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as e:
            return {
                "status": "error",
                "coordinate_assembly": label,
                "error": self._get_variant_error(e, variant_id, assembly),
            }

        payload = response.json()
        result = {
            "status": "success",
            "coordinate_assembly": label,
            "data": payload,
        }
        result.update(
            self._sibling_annotation_records(payload, variant_id, fields, assembly)
        )
        return result

    def _get_variant_error(self, exc: Exception, variant_id: str, assembly: str) -> str:
        """Name the assembly/id mismatch, which is the usual cause of a 404 here.

        /variant/<hgvs> is a verbatim key lookup, not a liftover: MyVariant
        files the GRCh37 and GRCh38 records for one variant under different
        ids, so asking for the hg19 id with assembly=hg38 is a 404 rather than
        a translated answer. A bare "request failed" sends the caller hunting
        for an outage instead of for the id they actually needed.
        """
        message = f"MyVariant.info API request failed: {str(exc)}"
        status = getattr(getattr(exc, "response", None), "status_code", None)
        if status == 404 and not RSID_PATTERN.match(variant_id.strip()):
            message += (
                f" No record with id '{variant_id}' exists in "
                f"{self.ASSEMBLY_LABELS[assembly]}. MyVariant looks HGVS ids up "
                "verbatim and never lifts coordinates over, so the id must already "
                "be written in the assembly you asked for. Supply the id for that "
                "assembly, switch `assembly`, or pass the rsID, which resolves in "
                "either."
            )
        return message

    @staticmethod
    def _field_roots(record: Any) -> set:
        """Top-level field names present on one MyVariant record."""
        return set(record) if isinstance(record, dict) else set()

    def _requested_annotation_roots(self, fields: str) -> set:
        """Which of the requested fields would carry an annotation.

        `all` and `*` name no field in particular, so they fall back to the
        list this tool declares: asking MyVariant for everything is still
        asking it for the scores, and treating it as "nothing requested" would
        switch the cross-check off on the broadest possible request.
        """
        text = str(fields).strip().lower()
        if text in ("", "all", "*"):
            text = self._declared_fields_default().lower()
        roots = {part.strip().split(".")[0] for part in text.split(",")}
        return {root for root in roots if root} - self.IDENTITY_FIELD_ROOTS

    def _sibling_annotation_records(
        self, payload: Any, variant_id: str, fields: str, assembly: str
    ) -> Dict[str, Any]:
        """Surface records filed under the same rsID that do carry the data.

        MyVariant can hold several records for one rsID, and /variant/<rsid>
        answers with the highest-scoring one. For rs267606617 that is
        chrMT:m.1555A>G, a dbSNP-only stub, while the CADD score lives on the
        sibling chrMT:g.1555A>G -- so a tool whose whole job is pathogenicity
        scores replied "no scores" for a variant that has one.

        The sibling records are reported alongside the primary one, never in
        place of it: `data` stays exactly what MyVariant resolved, so a caller
        reading it keeps reading the same record it always did.

        The extra request is confined to the case that motivates it -- an rsID
        input whose resolved record carries none of the requested annotation
        fields -- so the common path costs nothing.
        """
        if not RSID_PATTERN.match(variant_id.strip()):
            return {}
        wanted = self._requested_annotation_roots(fields)
        if not wanted:
            return {}

        primary = payload if isinstance(payload, list) else [payload]
        if any(self._field_roots(record) & wanted for record in primary):
            return {}

        # Reuse the /query handler so the assembly rule stays in one place.
        found = self._query_variants(
            {"query": variant_id, "fields": fields, "size": 10, "assembly": assembly}
        )
        try:
            hits = found["data"]["hits"]
        except (KeyError, TypeError):
            # A cross-check is a bonus; failing it must not fail the answer.
            return {}

        primary_ids = {
            record.get("_id") for record in primary if isinstance(record, dict)
        }
        siblings = [
            hit
            for hit in hits
            if isinstance(hit, dict)
            and hit.get("_id") not in primary_ids
            and self._field_roots(hit) & wanted
        ]
        if not siblings:
            return {}

        sibling_ids = [hit["_id"] for hit in siblings]
        resolved = ", ".join(sorted(str(i) for i in primary_ids if i)) or "a record"
        return {
            "sibling_variant_ids_with_requested_fields": sibling_ids,
            "sibling_records_with_requested_fields": siblings,
            "sibling_record_note": (
                f"MyVariant.info files more than one record under {variant_id}. "
                f"/variant/{variant_id} resolves to the highest-scoring one "
                f"({resolved}), which carries none of the requested "
                f"{', '.join(sorted(wanted))} fields, while "
                f"{', '.join(str(i) for i in sibling_ids)} does. `data` is left "
                "exactly as MyVariant returned it; the record(s) carrying the "
                "requested fields are in `sibling_records_with_requested_fields`."
            ),
        }


@register_tool("MyChemTool")
class MyChemTool(BaseTool):
    """
    Tool for querying MyChem.info API.

    MyChem.info provides chemical/drug annotation data from 30+ sources
    for 90M+ chemicals and drugs.

    No authentication required. Free for academic/research use.
    """

    MYCHEM_BASE_URL = "https://mychem.info/v1"

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.operation = tool_config.get("fields", {}).get("operation", "query")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the MyChem.info API call."""
        operation = self.operation

        if operation == "query":
            return self._query_chemicals(arguments)
        elif operation == "get_chemical":
            return self._get_chemical(arguments)
        else:
            return {"status": "error", "error": f"Unknown operation: {operation}"}

    def _query_chemicals(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Query chemicals/drugs by name, InChIKey, or other identifiers.

        Endpoint: GET /query
        """
        query = arguments.get("query", "")
        fields = arguments.get("fields", "drugbank,chebi,pubchem,chembl")
        size = arguments.get("size", 10)

        if not query:
            return {"status": "error", "error": "Query parameter is required"}

        params = {"q": query, "fields": fields, "size": min(size, 100)}

        try:
            response = requests.get(
                f"{self.MYCHEM_BASE_URL}/query", params=params, timeout=self.timeout
            )
            response.raise_for_status()
            return {"status": "success", "data": response.json()}
        except requests.RequestException as e:
            return {
                "status": "error",
                "error": f"MyChem.info API request failed: {str(e)}",
            }

    def _get_chemical(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get detailed chemical annotation by InChIKey or other ID.

        Endpoint: GET /chem/<chemid>
        """
        chem_id = arguments.get("chem_id", "")
        fields = arguments.get("fields", "drugbank,chebi,pubchem,chembl,drugcentral")

        if not chem_id:
            return {
                "status": "error",
                "error": "chem_id parameter is required (InChIKey recommended)",
            }

        params = {"fields": fields}

        try:
            response = requests.get(
                f"{self.MYCHEM_BASE_URL}/chem/{chem_id}",
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return {"status": "success", "data": response.json()}
        except requests.RequestException as e:
            return {
                "status": "error",
                "error": f"MyChem.info API request failed: {str(e)}",
            }
