"""
PheWAS (Phenome-Wide Association Study) tools for ToolUniverse.

Cross-biobank PheWAS coverage. Given a single variant, these tools return every
phenotype associated with it in a population biobank — the inverse of a GWAS
(which fixes a phenotype and scans variants). This is the standard workflow for
cross-ancestry replication and pleiotropy assessment.

Biobanks covered (all PheWeb-based, public, no authentication):
  - BioBank Japan (BBJ)   https://pheweb.jp                  (Japanese, GRCh37)
  - UKB-TOPMed            https://pheweb.org/UKB-TOPMed      (European/UKB, GRCh38)
  - TPMI                  https://pheweb.ibms.sinica.edu.tw  (Taiwanese, GRCh38)

Plus Genebass for exome-wide gene-level burden PheWAS (GRCh38):
  - Genebass             https://main.genebass.org          (UK Biobank 394K exomes)

Together with the existing FinnGen tools (Finnish), these enable replication of a
genetic association across European, Japanese, Taiwanese, and UK ancestries.
"""

import re
import ssl
import requests
from typing import Dict, Any, List, Optional, Tuple

from .base_tool import BaseTool
from .tool_registry import register_tool


class _RelaxedStrictAdapter(requests.adapters.HTTPAdapter):
    """HTTPS adapter that keeps full CA-chain + hostname verification but clears
    OpenSSL 3.x's VERIFY_X509_STRICT flag.

    Some public data servers (e.g. TPMI) ship certificates that omit the Subject
    Key Identifier extension, which OpenSSL 3.x rejects in strict mode even though
    the certificate chains to a trusted root. This relaxes only that pedantic
    check; untrusted, expired, self-signed, or wrong-host certificates are still
    rejected, so it is NOT equivalent to verify=False.
    """

    def init_poolmanager(self, *args, **kwargs):
        import certifi
        from urllib3.util.ssl_ import create_urllib3_context

        ctx = create_urllib3_context()
        ctx.load_verify_locations(certifi.where())
        ctx.verify_flags &= ~ssl.VERIFY_X509_STRICT
        kwargs["ssl_context"] = ctx
        return super().init_poolmanager(*args, **kwargs)


# Per-biobank configuration: base URL, genome build, and the Ensembl REST server
# used to resolve rsIDs to coordinates in that biobank's build.
_PHEWEB_BIOBANKS = {
    "bbj": {
        "label": "BioBank Japan",
        "base_url": "https://pheweb.jp",
        "build": "GRCh37",
        "ensembl_server": "https://grch37.rest.ensembl.org",
        "ancestry": "Japanese",
    },
    "ukb_topmed": {
        "label": "UKB-TOPMed",
        "base_url": "https://pheweb.org/UKB-TOPMed",
        "build": "GRCh38",
        "ensembl_server": "https://rest.ensembl.org",
        "ancestry": "European (UK Biobank)",
    },
    "tpmi": {
        "label": "TPMI (Taiwan Precision Medicine Initiative)",
        "base_url": "https://pheweb.ibms.sinica.edu.tw",
        "build": "GRCh38",
        "ensembl_server": "https://rest.ensembl.org",
        "ancestry": "Taiwanese (Han Chinese)",
        # The TPMI host serves a certificate that fails OpenSSL 3.x *strict*
        # verification ("Missing Subject Key Identifier"). It still chains to a
        # trusted CA, so for this host only we relax the strict-X509 flag while
        # keeping full CA-chain + hostname verification (untrusted certs are
        # still rejected).
        "relax_tls_strictness": True,
    },
}

# Some hosts (e.g. TPMI behind openresty) reject non-browser user agents.
_BROWSER_UA = "Mozilla/5.0 (compatible; ToolUniverse/1.0; +https://aiscientist.tools)"
_JSON_HEADERS = {"Accept": "application/json", "User-Agent": _BROWSER_UA}

_RSID_RE = re.compile(r"^rs\d+$", re.IGNORECASE)
_VARIANT_RE = re.compile(
    r"^(?:chr)?(\w+)[:\-](\d+)[:\-]([ACGTN]+)[:\-]([ACGTN]+)$", re.IGNORECASE
)


def _resolve_rsid(
    rsid: str, server: str, build: str, timeout: int
) -> Tuple[List[str], Optional[str]]:
    """Resolve an rsID to candidate chr:pos-ref-alt variants in the requested build.

    Returns (candidates, error_message). Multi-allelic SNPs (e.g. allele_string
    "C/G/T") yield one candidate per alternate allele, since the caller cannot
    know which alt the biobank recorded; the caller tries each in turn.
    """
    url = f"{server}/variation/human/{rsid}"
    resp = requests.get(
        url, headers={"Content-Type": "application/json"}, timeout=timeout
    )
    if resp.status_code == 404:
        return [], f"rsID '{rsid}' not found in Ensembl ({build})"
    resp.raise_for_status()
    candidates: List[str] = []
    for m in resp.json().get("mappings", []):
        if m.get("assembly_name") != build:
            continue
        alleles = (m.get("allele_string") or "").split("/")
        chrom = m.get("seq_region_name")
        pos = m.get("start")
        if len(alleles) < 2 or not chrom or not pos:
            continue
        ref = alleles[0]
        for alt in alleles[1:]:
            cand = f"{chrom}:{pos}-{ref}-{alt}"
            if cand not in candidates:
                candidates.append(cand)
    if not candidates:
        return [], f"rsID '{rsid}' has no {build} mapping with a clear ref/alt allele"
    return candidates, None


def _filter_and_sort_by_pval(
    associations: List[Dict[str, Any]], max_pval: Optional[float]
) -> List[Dict[str, Any]]:
    """Drop associations above max_pval (if given) and sort ascending by p-value.

    Non-numeric p-values are treated as 1.0 so they sort last and are excluded by
    any max_pval filter.
    """
    if max_pval is not None:
        associations = [
            a
            for a in associations
            if isinstance(a["pval"], (int, float)) and a["pval"] <= max_pval
        ]
    associations.sort(
        key=lambda a: a["pval"] if isinstance(a["pval"], (int, float)) else 1.0
    )
    return associations


def _canonicalize_variant(variant: str) -> Optional[str]:
    """Normalize a chr:pos:ref:alt / chr-pos-ref-alt string to PheWeb's chr:pos-ref-alt."""
    m = _VARIANT_RE.match(variant.strip())
    if not m:
        return None
    chrom, pos, ref, alt = m.groups()
    return f"{chrom}:{pos}-{ref.upper()}-{alt.upper()}"


@register_tool("PheWebPheWASTool")
class PheWebPheWASTool(BaseTool):
    """Variant-level PheWAS lookup across PheWeb-based population biobanks.

    The target biobank is selected by ``fields.biobank`` (bbj | ukb_topmed | tpmi).
    Accepts either an rsID (resolved to the biobank's build via Ensembl) or an
    explicit ``chr:pos:ref:alt`` variant already in that build.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        biobank_key = tool_config.get("fields", {}).get("biobank", "ukb_topmed")
        self.biobank_key = biobank_key
        self.cfg = _PHEWEB_BIOBANKS.get(biobank_key)
        self._http: Optional[requests.Session] = None

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if self.cfg is None:
            return {
                "status": "error",
                "error": f"Unknown biobank '{self.biobank_key}'. Expected one of: {', '.join(_PHEWEB_BIOBANKS)}",
            }
        try:
            return self._run(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"{self.cfg['label']} PheWAS request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": f"Failed to connect to {self.cfg['label']} PheWAS API",
            }
        except Exception as e:  # noqa: BLE001 - tools must never raise
            return {
                "status": "error",
                "error": f"{self.cfg['label']} PheWAS error: {str(e)}",
            }

    def _run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        warnings: List[str] = []
        candidates, err = self._resolve_input(arguments, warnings)
        if err:
            return {"status": "error", "error": err}

        limit = arguments.get("limit", 20)
        max_pval = arguments.get("max_pval")

        # Try each candidate variant (multi-allelic rsIDs yield several) and use
        # the one actually present in the biobank. PheWeb returns HTTP 200 with a
        # null/empty body for absent variants, so select by presence of phenos.
        canonical = candidates[0]
        data = None
        candidate_errors: List[str] = []
        for cand in candidates:
            try:
                resp = self._get(f"{self.cfg['base_url']}/api/variant/{cand}")
                if resp.status_code == 404:
                    continue
                resp.raise_for_status()
                payload = resp.json()
            except requests.exceptions.RequestException as e:
                # A transient failure (e.g. 500/502) on one candidate must not
                # abort the lookup; a later candidate may still resolve.
                candidate_errors.append(f"{cand}: {str(e)}")
                continue
            if isinstance(payload, dict) and payload.get("phenos"):
                canonical = cand
                data = payload
                break

        # Only surface an error if every candidate failed to fetch (none reached
        # a usable 200/404 response).
        if (
            data is None
            and candidate_errors
            and len(candidate_errors) == len(candidates)
        ):
            return {
                "status": "error",
                "error": (
                    f"{self.cfg['label']} PheWAS lookup failed for all candidates: "
                    + "; ".join(candidate_errors)
                ),
            }

        if data is None:
            tried = ", ".join(candidates)
            return {
                "status": "success",
                "data": {"variant": candidates[0], "associations": []},
                "metadata": {
                    "source": self.cfg["label"],
                    "build": self.cfg["build"],
                    "total_associations": 0,
                    "note": f"Variant not present in {self.cfg['label']} ({self.cfg['build']}); tried {tried}",
                    "warnings": warnings,
                },
            }

        # data is guaranteed to be a dict with non-empty "phenos" here (selected above).
        phenos = data.get("phenos", [])
        associations = [
            {
                "phenocode": p.get("phenocode"),
                "phenostring": p.get("phenostring"),
                "category": p.get("category"),
                "pval": p.get("pval"),
                "beta": p.get("beta"),
                "sebeta": p.get("sebeta"),
                "af": p.get("af"),
                "num_cases": p.get("num_cases"),
                "num_controls": p.get("num_controls"),
            }
            for p in phenos
        ]
        associations = _filter_and_sort_by_pval(associations, max_pval)
        total = len(associations)
        truncated = total > limit

        return {
            "status": "success",
            "data": {
                "variant": canonical,
                "rsids": data.get("rsids"),
                "nearest_genes": data.get("nearest_genes"),
                "associations": associations[:limit],
            },
            "metadata": {
                "source": self.cfg["label"],
                "ancestry": self.cfg["ancestry"],
                "build": self.cfg["build"],
                "total_associations": total,
                "returned": min(limit, total),
                "truncated": truncated,
                "variant_url": f"{self.cfg['base_url']}/variant/{canonical}",
                "warnings": warnings,
            },
        }

    def _session(self) -> requests.Session:
        """A requests Session, using the relaxed-strict TLS adapter for hosts whose
        certificate omits the SKI extension (verification stays on; see adapter)."""
        if self._http is None:
            self._http = requests.Session()
            if self.cfg.get("relax_tls_strictness"):
                self._http.mount(self.cfg["base_url"], _RelaxedStrictAdapter())
        return self._http

    def _get(self, url: str) -> requests.Response:
        return self._session().get(url, headers=_JSON_HEADERS, timeout=self.timeout)

    def _resolve_input(
        self, arguments: Dict[str, Any], warnings: List[str]
    ) -> Tuple[List[str], Optional[str]]:
        """Return (candidate_variants, error). Handles rsID and explicit variant input."""
        rsid = (arguments.get("rsid") or "").strip()
        variant = (arguments.get("variant") or "").strip()

        # A bare rsID passed in the variant slot is still an rsID.
        if not rsid and _RSID_RE.match(variant):
            rsid, variant = variant, ""

        if rsid:
            if not _RSID_RE.match(rsid):
                return [], f"Invalid rsID '{rsid}' (expected e.g. rs7903146)"
            candidates, err = _resolve_rsid(
                rsid, self.cfg["ensembl_server"], self.cfg["build"], self.timeout
            )
            if err:
                return [], err
            warnings.append(
                f"Resolved {rsid} to {len(candidates)} candidate variant(s) "
                f"on {self.cfg['build']} via Ensembl: {', '.join(candidates)}"
            )
            return candidates, None

        if variant:
            canonical = _canonicalize_variant(variant)
            if not canonical:
                return [], (
                    f"Invalid variant '{variant}'. Expected chr:pos:ref:alt "
                    f"(e.g. 10:112998590:C:T) in {self.cfg['build']}, or an rsID."
                )
            return [canonical], None

        return (
            [],
            "Provide either 'rsid' (e.g. rs7903146) or 'variant' (chr:pos:ref:alt)",
        )


# Genebass canonical burden sets and their accepted aliases.
_GENEBASS_BURDEN = {
    "plof": "pLoF",
    "lof": "pLoF",
    "missense": "missense|LC",
    "missenselc": "missense|LC",
    "synonymous": "synonymous",
}
_ENSG_RE = re.compile(r"^ENSG\d+", re.IGNORECASE)

# The fields that jointly identify a Genebass phenotype. The same composite key
# is built from the /phenotypes catalogue and from each /phewas row so the two
# can be joined for human-readable descriptions; they MUST stay in sync.
_GENEBASS_PHENO_KEY_FIELDS = (
    "trait_type",
    "phenocode",
    "pheno_sex",
    "coding",
    "modifier",
)


def _genebass_pheno_key(record: Dict[str, Any]) -> str:
    return "-".join(str(record.get(k, "")) for k in _GENEBASS_PHENO_KEY_FIELDS)


@register_tool("GenebassTool")
class GenebassTool(BaseTool):
    """Exome-wide gene-level burden PheWAS from Genebass (UK Biobank 394K exomes).

    Given one gene, returns its rare-variant burden association across ~4,500
    phenotypes (GRCh38). Complements variant-level PheWAS by aggregating rare
    coding variants into a single gene-level test (SAIGE-GENE+).
    """

    BASE_URL = "https://main.genebass.org/api"

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self._desc_cache: Optional[Dict[str, str]] = None

    def _phenotype_descriptions(self) -> Dict[str, str]:
        """Map the composite phenotype key to its human-readable description (cached).

        Keyed by _genebass_pheno_key (trait_type-phenocode-pheno_sex-coding-modifier),
        matching the key built from each /phewas row so descriptions can be joined.
        """
        if self._desc_cache is not None:
            return self._desc_cache
        cache: Dict[str, str] = {}
        try:
            resp = requests.get(
                f"{self.BASE_URL}/phenotypes",
                headers=_JSON_HEADERS,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            for p in resp.json():
                if p.get("description"):
                    cache[_genebass_pheno_key(p)] = p["description"]
        except (requests.RequestException, ValueError):
            # Descriptions are a nicety; absence must not fail the main lookup.
            pass
        self._desc_cache = cache
        return cache

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return self._run(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"Genebass request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to Genebass API"}
        except Exception as e:  # noqa: BLE001 - tools must never raise
            return {"status": "error", "error": f"Genebass error: {str(e)}"}

    def _run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        warnings: List[str] = []
        gene_input = (arguments.get("gene") or "").strip()
        if not gene_input:
            return {
                "status": "error",
                "error": "gene is required (Ensembl gene ID or symbol)",
            }

        burden_raw = (arguments.get("burden_set") or "pLoF").strip()
        burden_key = re.sub(r"[^a-z0-9]", "", burden_raw.lower())
        burden = _GENEBASS_BURDEN.get(burden_key)
        if burden is None:
            return {
                "status": "error",
                "error": (
                    f"Invalid burden_set '{burden_raw}'. Allowed: pLoF, missense|LC, "
                    "synonymous (aliases: lof/plof -> pLoF, missense -> missense|LC)"
                ),
            }

        gene_id, err = self._resolve_gene(gene_input, warnings)
        if err:
            return {"status": "error", "error": err}

        limit = arguments.get("limit", 25)
        max_pval = arguments.get("max_pval")

        url = (
            f"{self.BASE_URL}/phewas/{gene_id}?burdenSet={requests.utils.quote(burden)}"
        )
        resp = requests.get(url, headers=_JSON_HEADERS, timeout=self.timeout)
        if resp.status_code == 404:
            return {
                "status": "error",
                "error": f"Gene '{gene_id}' not found in Genebass",
            }
        resp.raise_for_status()
        data = resp.json()

        gene_meta = data.get("gene", {}) if isinstance(data, dict) else {}
        rows = data.get("phewas", []) if isinstance(data, dict) else []
        associations = [
            {
                "phenocode": r.get("phenocode"),
                "description": None,
                "trait_type": r.get("trait_type"),
                "pval": r.get("Pvalue_Burden"),
                "pval_skat": r.get("Pvalue_SKAT"),
                "beta": r.get("BETA_Burden"),
                "total_variants": r.get("total_variants"),
                "_key": _genebass_pheno_key(r),
            }
            for r in rows
        ]
        associations = _filter_and_sort_by_pval(associations, max_pval)
        total = len(associations)
        # Phewas rows carry no human-readable phenotype name; join the top hits
        # against the phenotype catalogue (one cached lookup) for readability.
        top = associations[:limit]
        desc_map = self._phenotype_descriptions()
        for a in top:
            a["description"] = desc_map.get(a.pop("_key"))
        for a in associations[limit:]:
            a.pop("_key", None)

        return {
            "status": "success",
            "data": {
                "gene_id": gene_meta.get("gene_id", gene_id),
                "gene_symbol": gene_meta.get("symbol"),
                "burden_set": burden,
                "associations": top,
            },
            "metadata": {
                "source": "Genebass (UK Biobank 394K exomes, SAIGE-GENE+)",
                "build": "GRCh38",
                "total_associations": total,
                "returned": min(limit, total),
                "truncated": total > limit,
                "gene_url": f"https://genebass.org/gene/{gene_id}",
                "warnings": warnings,
            },
        }

    def _resolve_gene(
        self, gene_input: str, warnings: List[str]
    ) -> Tuple[Optional[str], Optional[str]]:
        """Resolve a gene symbol to an Ensembl gene ID; pass through ENSG IDs."""
        if _ENSG_RE.match(gene_input):
            return gene_input.split(".", 1)[0].upper(), None

        url = f"https://rest.ensembl.org/xrefs/symbol/homo_sapiens/{gene_input}"
        resp = requests.get(
            url, headers={"Content-Type": "application/json"}, timeout=self.timeout
        )
        if resp.status_code == 404:
            return None, f"Gene symbol '{gene_input}' not found in Ensembl"
        resp.raise_for_status()
        for xref in resp.json():
            if str(xref.get("id", "")).upper().startswith("ENSG"):
                ensg = xref["id"].split(".", 1)[0].upper()
                warnings.append(f"Resolved symbol '{gene_input}' to {ensg} via Ensembl")
                return ensg, None
        return None, f"No Ensembl gene ID found for symbol '{gene_input}'"
