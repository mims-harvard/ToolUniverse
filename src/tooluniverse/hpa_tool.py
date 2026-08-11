# hpa_tool.py

import re
import requests
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, NamedTuple, Optional, Tuple
from .base_tool import BaseTool
from .tool_registry import register_tool

HPA_SEARCH_API = "https://www.proteinatlas.org/api/search_download.php"
HPA_BASE = "https://www.proteinatlas.org"
HPA_JSON_API_TEMPLATE = "https://www.proteinatlas.org/{ensembl_id}.json"
HPA_XML_API_TEMPLATE = "https://www.proteinatlas.org/{ensembl_id}.xml"

# ---------------------------------------------------------------------------
# HPA download-column catalogue
# ---------------------------------------------------------------------------
# search_download.php SILENTLY DROPS any column code it does not recognise: an
# unknown code and a gene with no data produce byte-identical responses. Every
# code below is an exact `data-abbr` value scraped from
# https://www.proteinatlas.org/search and re-verified against the live API.
# Do not invent codes here -- a wrong one is indistinguishable from "no data"
# and gets blamed on the caller's input.
#
# Fix-R31: several previously-mapped names had no matching column, e.g.
#   ?columns=g,eg,t_RNA_skin,t_RNA_skin_1,t_RNA_liver  ->
#   {"Gene":"NCSTN","Tissue RNA - liver [nTPM]":"48.9",
#    "Tissue RNA - skin 1 [nTPM]":"34.4"}       <- no "skin" key at all
# so 'skin' was reported as an unrecognised tissue name for every gene that is
# not skin-enriched. Likewise `rnascm`/`rnablm` are not column codes at all
# (the real ones are `rnascsm`/`rnabcsm`), so source_type single_cell and blood
# never returned anything.

# t_RNA_<x> -> "Tissue RNA - <x> [nTPM]" (consensus tissue panel, 51 tissues)
HPA_TISSUE_RNA_COLUMNS = (
    "adipose_tissue",
    "adrenal_gland",
    "amygdala",
    "appendix",
    "basal_ganglia",
    "blood_vessel",
    "bone_marrow",
    "breast",
    "cerebellum",
    "cerebral_cortex",
    "cervix",
    "choroid_plexus",
    "colon",
    "duodenum",
    "endometrium_1",
    "epididymis",
    "esophagus",
    "fallopian_tube",
    "gallbladder",
    "heart_muscle",
    "hippocampal_formation",
    "hypothalamus",
    "kidney",
    "liver",
    "lung",
    "lymph_node",
    "midbrain",
    "ovary",
    "pancreas",
    "parathyroid_gland",
    "pituitary_gland",
    "placenta",
    "prostate",
    "rectum",
    "retina",
    "salivary_gland",
    "seminal_vesicle",
    "skeletal_muscle",
    "skin_1",
    "small_intestine",
    "smooth_muscle",
    "spinal_cord",
    "spleen",
    "stomach_1",
    "testis",
    "thymus",
    "thyroid_gland",
    "tongue",
    "tonsil",
    "urinary_bladder",
    "vagina",
)

# brain_RNA_<x> -> "Brain RNA - <x> [nTPM]"
HPA_BRAIN_RNA_COLUMNS = (
    "amygdala",
    "basal_ganglia",
    "cerebellum",
    "cerebral_cortex",
    "choroid_plexus",
    "hippocampal_formation",
    "hypothalamus",
    "medulla_oblongata",
    "midbrain",
    "pons",
    "spinal_cord",
    "thalamus",
    "white_matter",
)

# blood_RNA_<x> -> "Blood RNA - <x> [nTPM]".  HPA's blood atlas publishes
# immune cell *subsets*; there is no aggregate "T-cell"/"B-cell"/"monocyte"
# column, hence the fan-out aliases below.
HPA_BLOOD_RNA_COLUMNS = (
    "basophil",
    "classical_monocyte",
    "eosinophil",
    "gdT-cell",
    "intermediate_monocyte",
    "MAIT_T-cell",
    "memory_B-cell",
    "memory_CD4_T-cell",
    "memory_CD8_T-cell",
    "myeloid_DC",
    "naive_B-cell",
    "naive_CD4_T-cell",
    "naive_CD8_T-cell",
    "neutrophil",
    "NK-cell",
    "non-classical_monocyte",
    "plasmacytoid_DC",
    "T-reg",
    "total_PBMC",
)

# sc_RNA_<x> -> "Single Cell Type RNA - <x> [nCPM]".  Note the unit: single
# cell data is nCPM, NOT nTPM.  Codes are case-sensitive (sc_RNA_hepatocytes
# is dropped, sc_RNA_Hepatocytes is not).
HPA_SINGLE_CELL_RNA_COLUMNS = (
    "Adipocytes",
    "Adrenal_cortex_cells",
    "Adrenal_medulla_cells",
    "Alveolar_cells_type_1",
    "Alveolar_cells_type_2",
    "Astrocytes",
    "B-cells",
    "Basal_keratinocytes",
    "Basal_prostatic_cells",
    "Bergmann_glia",
    "Brain_excitatory_neurons",
    "Brain_inhibitory_neurons",
    "Breast_hormone-responsive_cells",
    "Breast_lactating_cells",
    "Breast_myoepithelial_cells",
    "Breast_secretory_cells",
    "Cardiomyocytes",
    "cDC",
    "Cholangiocytes",
    "Choroid_plexus_epithelial_cells",
    "Colonocytes",
    "Cone_photoreceptor_cells",
    "Conjunctival_goblet_cells",
    "Corticotrophs",
    "Cytotrophoblasts",
    "Decidual_stromal_cells",
    "Differentiating_spermatogonia",
    "Distal_convoluted_tubule_cells",
    "Early_primary_spermatocytes",
    "Early_spermatids",
    "Endometrial_ciliated_cells",
    "Endometrial_glandular_cells",
    "Endometrial_luminal_cells",
    "Endometrial_secretory_cells",
    "Endometrial_stromal_cells",
    "Enteric_stem_cells",
    "Enteric_transient_amplifying_cells",
    "Enterocytes",
    "Ependymal_cells",
    "Epicardial_cells",
    "Epididymal_basal_cells",
    "Epididymal_clear_cells",
    "Epididymal_efferent_duct_absorptive_cells",
    "Epididymal_efferent_duct_ciliated_cells",
    "Epididymal_principal_cells",
    "Erythrocyte_progenitors",
    "Erythrocytes",
    "Esophageal_apical_cells",
    "Esophageal_basal_cells",
    "Esophageal_suprabasal_cells",
    "Extravillous_trophoblasts",
    "Fallopian_secretory_cells",
    "Fallopian_tube_ciliated_cells",
    "Fibro-adipogenic_progenitors",
    "Fibroblasts",
    "Foveolar_cells",
    "Gastric_chief_cells",
    "Gastric_progenitor_cells",
    "Goblet_cells",
    "Gonadotrophs",
    "Granulosa_cells",
    "Hematopoietic_stem_cells",
    "Hepatic_stellate_cells",
    "Hepatocytes",
    "Hofbauer_cells",
    "Innate_lymphoid_cells",
    "Kupffer_cells",
    "Lacrimal_acinar_cells",
    "Lactotrophs",
    "Late_primary_spermatocytes",
    "Late_spermatids",
    "Leydig_cells",
    "Loop_of_henle_epithelial_cells",
    "Lymphatic_endothelial_cells",
    "Macrophages",
    "Mast_cells",
    "Medullary_thymic_epithelial_cells",
    "Megakaryocyte-Erythroid_progenitors",
    "Megakaryocyte_progenitors",
    "Megakaryocytes",
    "Melanocytes",
    "Mesothelial_cells",
    "Microglia",
    "Migrating_cytotrophoblasts",
    "Monocyte_progenitors",
    "monocytes",
    "Mucous_neck_cells",
    "Müller_glia",
    "Myonuclei",
    "Myosatellite_cells",
    "Neuroendocrine_cells",
    "Neutrophil_progenitors",
    "Neutrophils",
    "NK-cells",
    "Ocular_epithelial_cells",
    "Oligodendrocyte_progenitor_cells",
    "Oligodendrocytes",
    "Oocytes",
    "Other_brain_neurons",
    "Ovarian_stromal_cells",
    "Pancreatic_acinar_cells",
    "Pancreatic_duct_cells",
    "Pancreatic_islet_cells",
    "Paneth_cells",
    "Papillary_tip_epithelial_cells",
    "Parietal_cells",
    "pDCs",
    "Pericytes",
    "Peritubular_myoid_cells",
    "Pituicytes/FSCs",
    "Pituitary_stem_cells",
    "Plasma_cells",
    "Platelets",
    "Podocytes",
    "Prostatic_club_cells",
    "Prostatic_glandular_cells",
    "Prostatic_hillock_cells",
    "Proximal_tubule_cells",
    "Renal_collecting_duct_intercalated_cells",
    "Renal_collecting_duct_principal_cells",
    "Renal_connecting_tubule_cells",
    "Respiratory_basal_cells",
    "Respiratory_ciliated_cells",
    "Respiratory_deuterosomal_cells",
    "Respiratory_ionocytes",
    "Respiratory_secretory_cells",
    "Retinal_amacrine_cells",
    "Retinal_bipolar_cells",
    "Retinal_ganglion_cells",
    "Retinal_horizontal_cells",
    "Retinal_pigment_epithelial_cells",
    "Rod_photoreceptor_cells",
    "Salivary_acinar_cells",
    "Salivary_basal_cells",
    "Salivary_duct_cells",
    "Salivary_ionocytes",
    "Salivary_myoepithelial_cells",
    "Schwann_cells",
    "Sertoli_cells",
    "Smooth_muscle_cells",
    "Somatotrophs",
    "Submucosal_glandular_cells",
    "Suprabasal_keratinocytes",
    "Syncytiotrophoblasts",
    "T-cells",
    "Thymic_myoid_cells",
    "Thymocytes",
    "Thyrotrophs",
    "Transitional_alveolar_cells",
    "Tuft_cells",
    "Undifferentiated_spermatogonia",
    "Urothelial_cells",
    "Vascular_endothelial_cells",
    "Vascular_smooth_muscle_cells",
)


def hpa_slug(name: Any) -> str:
    """Normalise a tissue/cell-type name or column suffix to a comparison key.

    'Skin 1' / 'skin_1' -> 'skin_1'; 'T-reg' -> 't_reg'; 'Muller glia' and
    'Müller_glia' both collapse to 'm_ller_glia'.
    """
    return re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower()).strip("_")


def _column_alias_map(
    columns: tuple[str, ...],
    extra: dict[str, list[str]] | None = None,
    singularize: bool = False,
) -> dict[str, list[str]]:
    """Build {caller-supplied name -> [exact HPA column suffixes]}.

    Every column is registered under its own slug. `singularize` additionally
    registers a singular alias for plural columns ('Hepatocytes' ->
    'hepatocyte'), which is only sensible for the single cell catalogue.
    `extra` adds hand-written aliases and always wins.
    """
    aliases: dict[str, list[str]] = {}
    for column in columns:
        aliases.setdefault(hpa_slug(column), [column])
    if singularize:
        for column in columns:
            slug = hpa_slug(column)
            if slug.endswith("s") and not slug.endswith("ss"):
                aliases.setdefault(slug[:-1], [column])
    for name, targets in (extra or {}).items():
        aliases[hpa_slug(name)] = list(targets)
    return aliases


# Names HPA once published (or that callers reasonably try) for which HPA has
# NO RNA column at all -- verified live: every one of
# t_RNA_bronchus / t_RNA_nasopharynx / t_RNA_oral_mucosa / t_RNA_soft_tissue /
# brain_RNA_brainstem is dropped from the response. Reporting them as valid
# source names produced a permanent, unexplained "N/A".
HPA_UNAVAILABLE_SOURCES = {
    "tissue": {
        "bronchus": "HPA covers bronchus only in its protein/IHC tissue atlas; there is no consensus RNA nTPM column for it. Closest RNA tissues: 'lung'.",
        "nasopharynx": "HPA covers nasopharynx only in its protein/IHC tissue atlas; there is no consensus RNA nTPM column for it.",
        "oral_mucosa": "HPA covers oral mucosa only in its protein/IHC tissue atlas; there is no consensus RNA nTPM column for it. Closest RNA tissues: 'esophagus', 'tongue'.",
        "soft_tissue": "HPA covers soft tissue only in its protein/IHC tissue atlas; there is no consensus RNA nTPM column for it. Closest RNA tissues: 'adipose_tissue', 'smooth_muscle'.",
    },
    "brain": {
        "brainstem": "HPA's brain atlas has no 'brainstem' column; query its components instead: 'medulla_oblongata', 'pons', 'midbrain'.",
    },
    "blood": {},
    "single_cell": {},
}

HPA_TISSUE_COLUMN_ALIASES = _column_alias_map(
    HPA_TISSUE_RNA_COLUMNS,
    {
        # HPA suffixes its two re-sampled tissues with "_1"; callers say the
        # bare organ name.
        "skin": ["skin_1"],
        "stomach": ["stomach_1"],
        "endometrium": ["endometrium_1"],
        "hippocampus": ["hippocampal_formation"],
        "heart": ["heart_muscle"],
        "muscle": ["skeletal_muscle"],
        "brain": ["cerebral_cortex"],
        "cortex": ["cerebral_cortex"],
        "fat": ["adipose_tissue"],
        "adrenal": ["adrenal_gland"],
        "thyroid": ["thyroid_gland"],
        "pituitary": ["pituitary_gland"],
        "parathyroid": ["parathyroid_gland"],
        "salivary": ["salivary_gland"],
        "bladder": ["urinary_bladder"],
        "oesophagus": ["esophagus"],
        "gut": ["small_intestine"],
    },
)

HPA_BRAIN_COLUMN_ALIASES = _column_alias_map(
    HPA_BRAIN_RNA_COLUMNS,
    {
        "hippocampus": ["hippocampal_formation"],
        "cortex": ["cerebral_cortex"],
        "striatum": ["basal_ganglia"],
    },
)

HPA_BLOOD_COLUMN_ALIASES = _column_alias_map(
    HPA_BLOOD_RNA_COLUMNS,
    {
        # No aggregate lineage columns exist -- fan out to the subsets HPA
        # actually publishes, most-representative first.
        "t_cell": [
            "T-reg",
            "naive_CD4_T-cell",
            "memory_CD4_T-cell",
            "naive_CD8_T-cell",
            "memory_CD8_T-cell",
            "MAIT_T-cell",
            "gdT-cell",
        ],
        "b_cell": ["naive_B-cell", "memory_B-cell"],
        "nk_cell": ["NK-cell"],
        "monocyte": [
            "classical_monocyte",
            "intermediate_monocyte",
            "non-classical_monocyte",
        ],
        "dendritic_cell": ["myeloid_DC", "plasmacytoid_DC"],
        "pbmc": ["total_PBMC"],
    },
)

HPA_SINGLE_CELL_COLUMN_ALIASES = _column_alias_map(
    HPA_SINGLE_CELL_RNA_COLUMNS,
    {
        "t_cell": ["T-cells"],
        "b_cell": ["B-cells"],
        "nk_cell": ["NK-cells"],
        "neuron": [
            "Brain_excitatory_neurons",
            "Brain_inhibitory_neurons",
            "Other_brain_neurons",
        ],
        "keratinocyte": ["Basal_keratinocytes", "Suprabasal_keratinocytes"],
        "dendritic_cell": ["cDC", "pDCs"],
    },
    singularize=True,
)

# source_type -> column prefix, unit, alias map and the canonical HPA names
# (used for error messages -- the alias map also holds synonyms and would make
# the list several times longer than the catalogue it describes).  The unit is
# HPA's, not a guess: sc_RNA_* columns are labelled [nCPM], the rest [nTPM].
HPA_SOURCE_COLUMNS: dict[str, dict[str, Any]] = {
    "tissue": {
        "prefix": "t_RNA_",
        "unit": "nTPM",
        "aliases": HPA_TISSUE_COLUMN_ALIASES,
        "canonical": HPA_TISSUE_RNA_COLUMNS,
    },
    "blood": {
        "prefix": "blood_RNA_",
        "unit": "nTPM",
        "aliases": HPA_BLOOD_COLUMN_ALIASES,
        "canonical": HPA_BLOOD_RNA_COLUMNS,
    },
    "brain": {
        "prefix": "brain_RNA_",
        "unit": "nTPM",
        "aliases": HPA_BRAIN_COLUMN_ALIASES,
        "canonical": HPA_BRAIN_RNA_COLUMNS,
    },
    "single_cell": {
        "prefix": "sc_RNA_",
        "unit": "nCPM",
        "aliases": HPA_SINGLE_CELL_COLUMN_ALIASES,
        "canonical": HPA_SINGLE_CELL_RNA_COLUMNS,
    },
}


def hpa_unit_from_column_label(label: Any, default: str = "") -> str:
    """Read the unit out of an HPA column header.

    'Single Cell Type RNA - Hepatocytes [nCPM]' -> 'nCPM'.  Never hard-code
    the unit: HPA reports single cell data in nCPM and everything else in
    nTPM, and mislabelling silently changes the meaning of the number.
    """
    match = re.search(r"\[([^\[\]]+)\]\s*$", str(label or ""))
    return match.group(1).strip() if match else default


# ---------------------------------------------------------------------------
# expression_level banding -- ToolUniverse's, NOT HPA's
# ---------------------------------------------------------------------------
# HPA's columns publish a bare nTPM/nCPM number and nothing else, so every
# `expression_level` this module emits is our own coarse banding of that
# number. It lands next to keys that ARE genuine HPA provenance (`source_field`
# names an actual HPA column, `expression_unit` comes from its header), where an
# unmarked "Very high" reads as HPA's verdict. So every response carrying
# `expression_level` also carries `expression_level_basis` naming ToolUniverse
# and quoting the exact cut-offs -- same disclosure voice as the `note` written
# when HPA's tissue name differs from the caller's -- and a reader can reproduce
# the banding from `expression_value` or disregard it. Deliberately says nothing
# about HPA's own published classification, which is not established here.
#
# Every banding in this file is defined below, so the disclosed cut-offs cannot
# drift from the code applying them. (`HPA_get_comprehensive_gene_details...`
# is the one tool whose expression_level is genuinely HPA's -- it reads the
# <level> element out of HPA's XML -- and it does not use these.)


class ExpressionBanding(NamedTuple):
    """A coarse expression banding ToolUniverse applies to HPA's raw number.

    `bands` is ordered high-to-low; a value falling under all of them gets
    `floor`, and a non-numeric value (None, 'N/A') gets `unknown`.
    """

    bands: Tuple[Tuple[float, str], ...]
    floor: str
    unknown: str

    def categorize(self, value: Any) -> str:
        try:
            val = float(value)
        except (ValueError, TypeError):
            return self.unknown
        for cutoff, name in self.bands:
            if val > cutoff:
                return name
        return self.floor

    def basis(self, unit: str) -> str:
        """The disclosure string emitted as `expression_level_basis`."""
        cutoffs = ", ".join(f">{cutoff} = {name}" for cutoff, name in self.bands)
        return (
            "expression_level is computed by ToolUniverse from expression_value; "
            "it is not a classification reported by HPA. Cut-offs applied to the "
            f"{unit} value: {cutoffs}, <={self.bands[-1][0]} = {self.floor}. HPA "
            "publishes the number only, so recompute or ignore this banding as "
            "your analysis requires."
        )

    def basis_for(self, level: Any, unit: str) -> Optional[str]:
        """The disclosure for `level`, or None when no band was ever applied.

        Tested by membership rather than against a sentinel, so it is also
        correct for the levels callers write literally without consulting a
        banding at all ('No data', 'Unknown') -- those rows are already honest
        and need no cut-offs.
        """
        banded = {name for _, name in self.bands} | {self.floor}
        return self.basis(unit) if level in banded else None

    def titled(self) -> "ExpressionBanding":
        """The 'Very high' spelling some tools already emit.

        Derived rather than written out, so the cut-offs and the label wording
        stay single-sourced across both casings.
        """
        return ExpressionBanding(
            tuple((cutoff, name.capitalize()) for cutoff, name in self.bands),
            self.floor.capitalize(),
            self.unknown.capitalize(),
        )


HPA_EXPRESSION_BANDING = ExpressionBanding(
    ((50, "very high"), (10, "high"), (1, "medium"), (0.1, "low")),
    floor="very low",
    unknown="unknown",
)
HPA_EXPRESSION_BANDING_TITLE = HPA_EXPRESSION_BANDING.titled()

# HPAGetContextualBiologicalProcessTool bands the same kind of nTPM number, but
# with its own vocabulary and no >50 tier -- and it feeds the result into a
# prose `contextual_conclusion` and a `functional_relevance` verdict, so the
# invented cut-offs travel further there than anywhere else in this file. Kept
# verbatim (changing them would change that tool's answers); disclosed like the
# rest.
HPA_CONTEXTUAL_EXPRESSION_BANDING = ExpressionBanding(
    (
        (10, "highly expressed"),
        (1, "moderately expressed"),
        (0.1, "expressed at low level"),
    ),
    floor="not expressed or very low",
    unknown="expression level unclear",
)


# --- Base Tool Classes ---


@register_tool("HPASearchApiTool")
class HPASearchApiTool(BaseTool):
    """
    Base class for interacting with HPA's search_download.php API.
    Uses HPA's search and download API to get protein expression data.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.timeout = 30
        self.base_url = HPA_SEARCH_API

    def _make_api_request(
        self, search_term: str, columns: str, format_type: str = "json"
    ) -> Dict[str, Any]:
        """Make HPA API request with improved error handling"""
        params = {
            "search": search_term,
            "format": format_type,
            "columns": columns,
            "compress": "no",
        }

        try:
            resp = requests.get(self.base_url, params=params, timeout=self.timeout)
            if resp.status_code == 404:
                return {
                    "status": "error",
                    "error": f"No data found for gene '{search_term}'",
                }
            if resp.status_code != 200:
                return {
                    "status": "error",
                    "error": f"HPA API request failed, HTTP {resp.status_code}",
                    "detail": resp.text,
                }

            if format_type == "json":
                data = resp.json()
                # Ensure we always return a list for consistency
                if not isinstance(data, list):
                    return {
                        "status": "error",
                        "error": "API did not return expected list format",
                    }
                return data
            else:
                return {"tsv_data": resp.text}

        except requests.RequestException as e:
            return {"status": "error", "error": f"HPA API request failed: {str(e)}"}
        except ValueError as e:
            return {
                "status": "error",
                "error": f"Failed to parse HPA response data: {str(e)}",
                "content": resp.text,
            }


@register_tool("HPAJsonApiTool")
class HPAJsonApiTool(BaseTool):
    """
    Base class for interacting with HPA's /{ensembl_id}.json API.
    More efficient for getting comprehensive gene data.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.timeout = 30
        self.base_url_template = HPA_JSON_API_TEMPLATE

    def _make_api_request(self, ensembl_id: str) -> Dict[str, Any]:
        """Make HPA JSON API request for a specific gene"""
        if not re.match(r"^ENS[A-Z]*G\d+(\.\d+)?$", ensembl_id.strip(), re.IGNORECASE):
            # HPA's endpoint 404s identically whether the ID is a
            # validly-formatted-but-unknown Ensembl Gene ID or simply the
            # wrong kind of identifier (e.g. a gene symbol like 'CLEC4C'
            # instead of 'ENSG00000198178'). Catch the format mismatch here so
            # the error tells the caller *why* nothing was found instead of
            # implying the gene itself has no HPA data.
            return {
                "status": "error",
                "error": (
                    f"'{ensembl_id}' is not a valid Ensembl Gene ID format "
                    "(expected e.g. 'ENSG00000141510'). This tool requires an "
                    "Ensembl Gene ID, not a gene symbol -- resolve the symbol "
                    "first (e.g. via Ensembl_lookup_gene_by_symbol)."
                ),
            }
        url = self.base_url_template.format(ensembl_id=ensembl_id)
        try:
            resp = requests.get(url, timeout=self.timeout)
            if resp.status_code == 404:
                return {
                    "status": "error",
                    "error": f"No data found for Ensembl ID '{ensembl_id}'",
                }
            if resp.status_code != 200:
                return {
                    "status": "error",
                    "error": f"HPA JSON API request failed, HTTP {resp.status_code}",
                    "detail": resp.text,
                }

            return resp.json()

        except requests.RequestException as e:
            return {
                "status": "error",
                "error": f"HPA JSON API request failed: {str(e)}",
            }
        except ValueError as e:
            return {
                "status": "error",
                "error": f"Failed to parse HPA JSON response: {str(e)}",
                "content": resp.text,
            }


@register_tool("HPAXmlApiTool")
class HPAXmlApiTool(BaseTool):
    """
    Base class for interacting with HPA's /{ensembl_id}.xml API.
    Optimized for comprehensive XML data extraction.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.timeout = 45
        self.base_url_template = HPA_XML_API_TEMPLATE

    def _make_api_request(self, ensembl_id: str) -> ET.Element:
        """Make HPA XML API request for a specific gene"""
        url = self.base_url_template.format(ensembl_id=ensembl_id)
        try:
            resp = requests.get(url, timeout=self.timeout)
            if resp.status_code == 404:
                raise Exception(f"No XML data found for Ensembl ID '{ensembl_id}'")
            if resp.status_code != 200:
                raise Exception(f"HPA XML API request failed, HTTP {resp.status_code}")

            return ET.fromstring(resp.content)
        except requests.RequestException as e:
            raise Exception(f"HPA XML API request failed: {str(e)}")
        except ET.ParseError as e:
            raise Exception(f"Failed to parse HPA XML response: {str(e)}")


@register_tool("HPASearchTool")
class HPASearchTool(HPASearchApiTool):
    """
    Generic search tool for Human Protein Atlas.

    This tool allows custom search queries and retrieval of specific columns from the
    Human Protein Atlas API. It provides more flexibility than the specialized tools
    by allowing direct access to the search API with custom parameters.

    Args:
        search_query (str): The search term to query for (e.g., gene name, description).
        columns (str, optional): Comma-separated list of columns to retrieve.
            Defaults to "g,gs,gd" (Gene, Gene synonym, Gene description).

            Available columns and their specifiers:
            - g: Gene name
            - gs: Gene synonym
            - gd: Gene description
            - e: Ensembl ID
            - u: UniProt ID
            - en: Enhanced
            - pe: Protein existence
            - r: Reliability
            - p: Pathology
            - c: Cancer
            - pt: Protein tissue
            - ptm: Predicted Transmembrane
            - s: Subcellular location
            - scml: Subcellular main location
            - scal: Subcellular additional location
            - rnat: RNA tissue specificity
            - rnats: RNA tissue specific score
            - rnatsm: RNA tissue specific nTPM
            - rnablm: RNA blood lineage specific nTPM
            - rnabrm: RNA brain region specific nTPM
            - rnascm: RNA single cell type specific nTPM

            See HPA API documentation for the full list of over 40 available columns.

        format (str, optional): Response format, "json" or "tsv". Defaults to "json".

    Returns:
        dict: A dictionary containing the search results.
            If successful, returns the API response (list of entries).
            If failed, returns a dictionary with an "error" key.

    Example:
        >>> tool = HPASearchTool()
        >>> result = tool.run({
        ...     "search_query": "p53",
        ...     "columns": "g,gs,scml,rnat",
        ...     "format": "json"
        ... })
        >>> print(result[0]["Gene"])
        TP53
    """

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the search tool.

        Args:
            arguments (Dict[str, Any]): Dictionary containing:
                - search_query (str): The term to search for.
                - columns (str, optional): Columns to retrieve.
                - format (str, optional): Response format.

        Returns:
            Dict[str, Any]: Search results or error message.
        """
        search_query = arguments.get("search_query")
        columns = arguments.get("columns", "g,gs,gd")
        format_type = arguments.get("format", "json")

        if not search_query:
            return {"status": "error", "error": "Parameter 'search_query' is required"}

        result = self._make_api_request(search_query, columns, format_type)
        if isinstance(result, dict) and result.get("status") == "error":
            return result
        return {"status": "success", "data": result}


# --- New Enhanced Tools Based on Your Optimization Plan ---


@register_tool("HPAGetRnaExpressionBySourceTool")
class HPAGetRnaExpressionBySourceTool(HPASearchApiTool):
    """
    Get RNA expression for a gene from specific biological sources using optimized columns parameter.
    This tool directly leverages the comprehensive columns table for efficient queries.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        # Aggregate "*specific nTPM" enrichment-summary columns, kept only as a
        # last-resort fallback. NOTE: of these four codes only `rnatsm` is a
        # real HPA column -- `rnablm`/`rnabrm`/`rnascm` are silently dropped
        # (the real codes are `rnabcsm`/`rnabrsm`/`rnascsm`). They are left
        # verbatim for backwards compatibility; the per-source columns below
        # are what actually answer a query, and they carry a value for every
        # gene rather than only the ones HPA classifies as enriched.
        self.source_column_mappings = {
            "tissue": "rnatsm",  # RNA tissue specific nTPM
            "blood": "rnablm",  # RNA blood lineage specific nTPM
            "brain": "rnabrm",  # RNA brain region specific nTPM
            "single_cell": "rnascm",  # RNA single cell type specific nTPM
        }

        # Fix-R4A-2 / Fix-R31: HPA silently drops unknown column codes, so a
        # bad code is indistinguishable from "no data" and the tool ended up
        # blaming the caller's source name. Prefixes and the per-source-name
        # column catalogue now come from HPA's published `data-abbr` list (see
        # the module header), so `single_cell` and `blood` return real numbers
        # instead of a permanent N/A.
        self.source_column_prefixes = {
            key: spec["prefix"] for key, spec in HPA_SOURCE_COLUMNS.items()
        }

        # HPA's unit differs per source family: single cell is nCPM, the rest
        # are nTPM. Never hard-code one unit for all of them.
        self.source_units = {
            key: spec["unit"] for key, spec in HPA_SOURCE_COLUMNS.items()
        }

        self.api_response_fields = {
            "tissue": "RNA tissue specific nTPM",
            "blood": "RNA blood lineage specific nTPM",
            "brain": "RNA brain region specific nTPM",
            "single_cell": "RNA single cell type specific nTPM",
        }

        # source_name -> the exact HPA column suffixes it resolves to. Values
        # are real column codes, not free-text guesses.
        self.source_name_mappings = {
            key: spec["aliases"] for key, spec in HPA_SOURCE_COLUMNS.items()
        }

        # The canonical HPA names behind those aliases, for error messages.
        self.source_canonical_names = {
            key: sorted(spec["canonical"], key=str.lower)
            for key, spec in HPA_SOURCE_COLUMNS.items()
        }

        # source_name -> why HPA cannot answer it at all (it has no RNA column).
        self.unavailable_sources = HPA_UNAVAILABLE_SOURCES

    @staticmethod
    def _categorize_expression(expression_value):
        """Bucket an nTPM/nCPM value into a coarse expression level."""
        return HPA_EXPRESSION_BANDING.categorize(expression_value)

    def _query_source_column(self, gene_name, source_type, candidate_names):
        """Fetch a source's value from its dedicated HPA column.

        `candidate_names` are exact HPA column suffixes, most-representative
        first; they are requested in a single call (HPA drops the ones it does
        not know without failing the request) and the first candidate that
        carries a value wins.

        Returns (value, column_label) or (None, None) when HPA has no such
        column or no value for this gene.
        """
        prefix = self.source_column_prefixes.get(source_type)
        if not prefix:
            return None, None

        columns = []
        for candidate in candidate_names:
            if not candidate:
                continue
            column = prefix + str(candidate).strip().replace(" ", "_")
            if column not in columns:
                columns.append(column)
        if not columns:
            return None, None

        try:
            response = self._make_api_request(gene_name, ",".join(["g"] + columns))
        except Exception:
            return None, None
        if not response or isinstance(response, dict):
            return None, None

        # HPA's search matches synonyms too (search=GFAP also returns HGFAC),
        # so pick the row whose Gene actually equals the query.
        row = next(
            (
                r
                for r in response
                if str(r.get("Gene", "")).upper() == str(gene_name).upper()
            ),
            response[0],
        )

        # HPA labels the columns e.g. "Brain RNA - thalamus [nTPM]" or
        # "Single Cell Type RNA - Hepatocytes [nCPM]"; match the part after
        # " RNA - " back to the requested suffix.
        by_slug = {}
        for key, value in row.items():
            if " RNA - " not in key:
                continue
            source_label = key.split(" RNA - ", 1)[1]
            source_label = re.sub(r"\s*\[[^\[\]]*\]\s*$", "", source_label)
            by_slug.setdefault(hpa_slug(source_label), (value, key))

        for candidate in candidate_names:
            hit = by_slug.get(hpa_slug(candidate))
            if hit and hit[0] not in (None, "", "N/A"):
                return hit

        # Lenient fallback: HPA returned a per-source column we could not tie
        # back to a candidate name (renamed column). Use it rather than
        # reporting "no data" for a value HPA clearly published.
        for value, key in by_slug.values():
            if value not in (None, "", "N/A"):
                return value, key
        return None, None

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        gene_name = arguments.get("gene_name")
        source_type = arguments.get("source_type", "").lower()
        source_name = (
            arguments.get("source_name", "").lower().replace(" ", "_").replace("-", "_")
        )

        if not gene_name:
            return {
                "status": "error",
                "data": {"error": "Parameter 'gene_name' is required"},
            }
        if not source_type:
            return {
                "status": "error",
                "data": {"error": "Parameter 'source_type' is required"},
            }
        if not source_name:
            return {
                "status": "error",
                "data": {"error": "Parameter 'source_name' is required"},
            }

        # Validate source type
        if source_type not in self.source_column_mappings:
            available_types = ", ".join(self.source_column_mappings.keys())
            return {
                "status": "error",
                "data": {
                    "error": f"Invalid source_type '{source_type}'. Available types: {available_types}"
                },
            }

        # Names HPA does not publish an RNA column for at all: say so
        # explicitly instead of returning a permanent, unexplained "N/A".
        unavailable = self.unavailable_sources.get(source_type, {})
        if source_name in unavailable:
            return {
                "status": "error",
                "data": {
                    "error": (
                        f"HPA has no RNA expression column for source_name "
                        f"'{source_name}' (source_type '{source_type}'). "
                        + unavailable[source_name]
                    )
                },
            }

        # Enhanced validation with intelligent recommendations
        if source_name not in self.source_name_mappings[source_type]:
            available_sources = sorted(self.source_name_mappings[source_type].keys())

            # Find similar source names (fuzzy matching)
            similar_sources = []
            source_keywords = source_name.replace("_", " ").split()

            for valid_source in available_sources:
                # Direct substring matching
                if (
                    source_name.lower() in valid_source.lower()
                    or valid_source.lower() in source_name.lower()
                ):
                    similar_sources.append(valid_source)
                    continue

                # Check with underscores removed/normalized
                normalized_input = source_name.lower().replace("_", "").replace(" ", "")
                normalized_valid = (
                    valid_source.lower().replace("_", "").replace(" ", "")
                )
                if (
                    normalized_input in normalized_valid
                    or normalized_valid in normalized_input
                ):
                    similar_sources.append(valid_source)
                    continue

                # Check individual keywords
                for keyword in source_keywords:
                    if (
                        keyword.lower() in valid_source.lower()
                        or valid_source.lower() in keyword.lower()
                    ):
                        similar_sources.append(valid_source)
                        break

            error_msg = (
                f"Invalid source_name '{source_name}' for source_type '{source_type}'. "
            )
            if similar_sources:
                error_msg += f"Similar options: {similar_sources[:3]}. "
            # HPA publishes ~160 single cell types; listing every alias makes
            # the message unusable, so show the canonical names and cap them.
            canonical = self.source_canonical_names[source_type]
            shown = canonical[:40]
            error_msg += (
                f"Valid HPA names for '{source_type}' ({len(canonical)} total): {shown}"
            )
            if len(canonical) > len(shown):
                error_msg += f" ... and {len(canonical) - len(shown)} more"
            return {"status": "error", "data": {"error": error_msg}}

        try:
            # Prefer HPA's dedicated per-source column -- it carries a value
            # for every gene, not just the ones enriched in this source type.
            candidates = list(self.source_name_mappings[source_type][source_name])
            candidates.append(source_name.replace("_", " "))
            direct_value, direct_label = self._query_source_column(
                gene_name, source_type, candidates
            )
            if direct_value is not None:
                # Unit comes from HPA's own column header, never a hard-coded
                # default: sc_RNA_* columns are [nCPM].
                unit = hpa_unit_from_column_label(
                    direct_label, self.source_units.get(source_type, "nTPM")
                )
                direct_level = self._categorize_expression(direct_value)
                data = {
                    "gene_name": gene_name,
                    "source_type": source_type,
                    "source_name": source_name,
                    "expression_value": direct_value,
                    "expression_level": direct_level,
                    "expression_unit": unit,
                    "column_queried": direct_label,
                    "status": "ok",
                }
                # Every other key here is genuine HPA provenance; mark the one
                # that is not.
                basis = HPA_EXPRESSION_BANDING.basis_for(direct_level, unit)
                if basis:
                    data["expression_level_basis"] = basis
                # If the request resolved to a differently-named HPA column
                # (an alias, or a subset standing in for an aggregate HPA does
                # not publish), say which column the number actually is.
                matched_label = direct_label.split(" RNA - ", 1)[-1]
                matched_label = re.sub(r"\s*\[[^\[\]]*\]\s*$", "", matched_label)
                if hpa_slug(matched_label) != hpa_slug(source_name):
                    others = [
                        c
                        for c in self.source_name_mappings[source_type][source_name]
                        if hpa_slug(c) != hpa_slug(matched_label)
                    ]
                    note = (
                        f"HPA has no column named '{source_name}' for source_type "
                        f"'{source_type}'; this value is from its '{matched_label}' "
                        "column."
                    )
                    if others:
                        note += f" Other columns this name covers: {others}."
                    data["note"] = note
                return {"status": "success", "data": data}

            # Get the correct API column
            api_column = self.source_column_mappings[source_type]
            columns = f"g,gs,{api_column}"

            # Call the search API
            response_data = self._make_api_request(gene_name, columns)

            if "error" in response_data:
                return {"status": "error", "data": response_data}

            if not response_data or len(response_data) == 0:
                result = {
                    "gene_name": gene_name,
                    "source_type": source_type,
                    "source_name": source_name,
                    "expression_value": "N/A",
                    "status": "Gene not found",
                }
                return {"status": "success", "data": result}

            # Get the first result
            gene_data = response_data[0]

            # Extract expression data from the API response
            expression_value = "N/A"
            available_sources = []

            # Get the expression data dictionary for this source type
            api_field_name = self.api_response_fields[source_type]
            expression_data = gene_data.get(api_field_name)

            if expression_data and isinstance(expression_data, dict):
                available_sources = list(expression_data.keys())

                # Get possible names for this source
                possible_names = self.source_name_mappings[source_type][source_name]

                # Try to find a matching source name in the response
                for source_key in expression_data.keys():
                    source_key_lower = source_key.lower()
                    for possible_name in possible_names:
                        if (
                            possible_name.lower() in source_key_lower
                            or source_key_lower in possible_name.lower()
                        ):
                            expression_value = expression_data[source_key]
                            break
                    if expression_value != "N/A":
                        break

                # If exact match not found, look for partial matches
                if expression_value == "N/A":
                    source_keywords = source_name.replace("_", " ").split()
                    for source_key in expression_data.keys():
                        source_key_lower = source_key.lower()
                        for keyword in source_keywords:
                            if keyword in source_key_lower:
                                expression_value = expression_data[source_key]
                                break
                        if expression_value != "N/A":
                            break

            expression_level = self._categorize_expression(expression_value)
            # Per-source-family unit, not a blanket "nTPM": HPA's single cell
            # columns are nCPM.
            unit = self.source_units.get(source_type, "nTPM")

            result = {
                "gene_name": gene_data.get("Gene", gene_name),
                "gene_synonym": gene_data.get("Gene synonym", ""),
                "source_type": source_type,
                "source_name": source_name,
                "expression_value": expression_value,
                "expression_level": expression_level,
                "expression_unit": unit,
                "column_queried": api_column,
                "available_sources": (
                    available_sources[:10]
                    if len(available_sources) > 10
                    else available_sources
                ),
                "total_available_sources": len(available_sources),
                "status": (
                    "success"
                    if expression_value != "N/A"
                    else "no_expression_data_for_source"
                ),
            }
            basis = HPA_EXPRESSION_BANDING.basis_for(expression_level, unit)
            if basis:
                result["expression_level_basis"] = basis
            if expression_value == "N/A":
                result["note"] = (
                    f"HPA's per-source column for '{source_name}' returned no value "
                    f"and the '{api_column}' enrichment-summary fallback carried "
                    "nothing either. 'N/A' here means HPA published no number for "
                    "this gene/source pair, not that the source name is invalid."
                )
            return {"status": "success", "data": result}

        except Exception as e:
            return {
                "status": "error",
                "data": {
                    "error": f"Failed to retrieve RNA expression data: {str(e)}",
                    "gene_name": gene_name,
                    "source_type": source_type,
                    "source_name": source_name,
                },
            }


@register_tool("HPAGetSubcellularLocationTool")
class HPAGetSubcellularLocationTool(HPASearchApiTool):
    """
    Get annotated subcellular locations for a protein using optimized columns parameter.
    Uses scml (main location) and scal (additional location) columns for efficient queries.
    """

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        gene_name = arguments.get("gene_name")
        if not gene_name:
            return {"status": "error", "error": "Parameter 'gene_name' is required"}

        # Use specific columns for subcellular location data
        result = self._make_api_request(gene_name, "g,gs,scml,scal")

        if "error" in result:
            return result

        if not result:
            return {"status": "error", "error": "No subcellular location data found"}

        gene_data = result[0]

        # Parse main and additional locations
        main_location = gene_data.get("Subcellular main location", "")
        additional_location = gene_data.get("Subcellular additional location", "")

        # Handle different data types (string or list)
        if isinstance(main_location, list):
            main_locations = main_location
        elif isinstance(main_location, str):
            main_locations = (
                [loc.strip() for loc in main_location.split(";") if loc.strip()]
                if main_location
                else []
            )
        else:
            main_locations = []

        if isinstance(additional_location, list):
            additional_locations = additional_location
        elif isinstance(additional_location, str):
            additional_locations = (
                [loc.strip() for loc in additional_location.split(";") if loc.strip()]
                if additional_location
                else []
            )
        else:
            additional_locations = []

        return {
            "status": "success",
            "data": {
                "gene_name": gene_data.get("Gene", gene_name),
                "gene_synonym": gene_data.get("Gene synonym", ""),
                "main_locations": main_locations,
                "additional_locations": additional_locations,
                "total_locations": len(main_locations) + len(additional_locations),
                "location_summary": self._generate_location_summary(
                    main_locations, additional_locations
                ),
            },
        }

    def _generate_location_summary(
        self, main_locs: List[str], add_locs: List[str]
    ) -> str:
        """Generate a summary of subcellular locations"""
        if not main_locs and not add_locs:
            return "No subcellular location data available"

        summary_parts = []
        if main_locs:
            summary_parts.append(f"Primary: {', '.join(main_locs)}")
        if add_locs:
            summary_parts.append(f"Additional: {', '.join(add_locs)}")

        return "; ".join(summary_parts)


# --- Existing Tools (Updated with improvements) ---


@register_tool("HPASearchGenesTool")
class HPASearchGenesTool(HPASearchApiTool):
    """
    Search for matching genes by gene name, keywords, or cell line names and return Ensembl ID list.
    This is the entry tool for many query workflows.
    """

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        search_query = arguments.get("search_query")
        if not search_query:
            return {"status": "error", "error": "Parameter 'search_query' is required"}

        # 'g' for Gene name, 'gs' for Gene synonym, 'eg' for Ensembl ID
        columns = "g,gs,eg"
        result = self._make_api_request(search_query, columns)

        if "error" in result:
            return result

        if not result or not isinstance(result, list):
            return {
                "status": "error",
                "error": f"No matching genes found for query '{search_query}'",
            }

        formatted_results = []
        for gene in result:
            gene_synonym = gene.get("Gene synonym", "")
            if isinstance(gene_synonym, str):
                synonyms = gene_synonym.split(", ") if gene_synonym else []
            elif isinstance(gene_synonym, list):
                synonyms = gene_synonym
            else:
                synonyms = []

            formatted_results.append(
                {
                    "gene_name": gene.get("Gene"),
                    "ensembl_id": gene.get("Ensembl"),
                    "gene_synonyms": synonyms,
                }
            )

        # Fix-R19D-1: HPA's search_download.php does a broad full-text
        # match with no server-side limit param (confirmed live: a
        # "limit" query param has no effect) -- a short, valid gene
        # symbol like "INS" returned 8,441 genes (1.4MB), many not even
        # containing the query as a substring. Rank exact gene-symbol
        # matches first and cap the response client-side; the caller can
        # raise max_results for a deliberately broad search.
        query_upper = search_query.upper()
        formatted_results.sort(
            key=lambda g: (g.get("gene_name") or "").upper() != query_upper
        )
        total_matches = len(formatted_results)
        max_results = arguments.get("max_results") or 50
        truncated_results = formatted_results[:max_results]

        return {
            "status": "success",
            "data": {
                "search_query": search_query,
                "match_count": len(truncated_results),
                "total_matches": total_matches,
                "truncated": total_matches > len(truncated_results),
                "genes": truncated_results,
            },
        }


@register_tool("HPAGetComparativeExpressionTool")
class HPAGetComparativeExpressionTool(HPASearchApiTool):
    """
    Compare gene expression levels in specific cell lines and healthy tissues.
    Get expression data for comparison by gene name and cell line name.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        # Mapping of common cell lines to their column identifiers
        self.cell_line_columns = {
            "ishikawa": "cell_RNA_ishikawa_heraklio",
            "hela": "cell_RNA_hela",
            "mcf7": "cell_RNA_mcf7",
            "a549": "cell_RNA_a549",
            "hepg2": "cell_RNA_hepg2",
            "jurkat": "cell_RNA_jurkat",
            "pc3": "cell_RNA_pc3",
            "rh30": "cell_RNA_rh30",
            "siha": "cell_RNA_siha",
            "u251": "cell_RNA_u251",
        }

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        gene_name = arguments.get("gene_name")
        cell_line = arguments.get("cell_line", "").lower()

        if not gene_name:
            return {"status": "error", "error": "Parameter 'gene_name' is required"}
        if not cell_line:
            return {"status": "error", "error": "Parameter 'cell_line' is required"}

        # Enhanced validation with intelligent recommendations
        cell_column = self.cell_line_columns.get(cell_line)
        if not cell_column:
            available_lines = list(self.cell_line_columns.keys())

            # Find similar cell line names
            similar_lines = []
            for valid_line in available_lines:
                if cell_line in valid_line or valid_line in cell_line:
                    similar_lines.append(valid_line)

            error_msg = f"Unsupported cell_line '{cell_line}'. "
            if similar_lines:
                error_msg += f"Similar options: {similar_lines}. "
            error_msg += f"All supported cell lines: {available_lines}"
            return {"status": "error", "error": error_msg}

        # Request expression data for the cell line
        cell_columns = f"g,gs,{cell_column}"
        cell_result = self._make_api_request(gene_name, cell_columns)
        if "error" in cell_result:
            return cell_result

        # Request expression data for healthy tissues
        tissue_columns = "g,gs,rnatsm"
        tissue_result = self._make_api_request(gene_name, tissue_columns)
        if "error" in tissue_result:
            return tissue_result

        # Format the result
        if not cell_result or not tissue_result:
            return {"status": "error", "error": "No expression data found"}

        # Extract the first matching gene data
        cell_data = (
            cell_result[0] if isinstance(cell_result, list) and cell_result else {}
        )
        tissue_data = (
            tissue_result[0]
            if isinstance(tissue_result, list) and tissue_result
            else {}
        )

        return {
            "status": "success",
            "data": {
                "gene_name": gene_name,
                "gene_symbol": cell_data.get("Gene", gene_name),
                "gene_synonym": cell_data.get("Gene synonym", ""),
                "cell_line": cell_line,
                "cell_line_expression": cell_data.get(cell_column, "N/A"),
                "healthy_tissue_expression": tissue_data.get(
                    "RNA tissue specific nTPM", "N/A"
                ),
                "expression_unit": "nTPM (normalized Transcripts Per Million)",
                "comparison_summary": self._generate_comparison_summary(
                    cell_data.get(cell_column),
                    tissue_data.get("RNA tissue specific nTPM"),
                ),
            },
        }

    def _generate_comparison_summary(self, cell_expr, tissue_expr) -> str:
        """Generate expression level comparison summary"""
        try:
            cell_val = float(cell_expr) if cell_expr and cell_expr != "N/A" else None
            tissue_val = (
                float(tissue_expr) if tissue_expr and tissue_expr != "N/A" else None
            )

            if cell_val is None or tissue_val is None:
                return "Insufficient data for comparison"

            if cell_val > tissue_val * 2:
                return f"Expression significantly higher in cell line ({cell_val:.2f} vs {tissue_val:.2f})"
            elif tissue_val > cell_val * 2:
                return f"Expression significantly higher in healthy tissues ({tissue_val:.2f} vs {cell_val:.2f})"
            else:
                return f"Expression levels similar (cell line: {cell_val:.2f}, healthy tissues: {tissue_val:.2f})"
        except Exception:
            return "Failed to calculate expression level comparison"


@register_tool("HPAGetDiseaseExpressionTool")
class HPAGetDiseaseExpressionTool(HPASearchApiTool):
    """
    Get expression data for a gene in specific diseases and tissues.
    Get related expression information by gene name, tissue type, and disease name.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        # Mapping of common cancer types to their column identifiers
        self.cancer_columns = {
            "brain_cancer": "cancer_RNA_brain_cancer",
            "breast_cancer": "cancer_RNA_breast_cancer",
            "colon_cancer": "cancer_RNA_colon_cancer",
            "lung_cancer": "cancer_RNA_lung_cancer",
            "liver_cancer": "cancer_RNA_liver_cancer",
            "prostate_cancer": "cancer_RNA_prostate_cancer",
            "kidney_cancer": "cancer_RNA_kidney_cancer",
            "pancreatic_cancer": "cancer_RNA_pancreatic_cancer",
            "stomach_cancer": "cancer_RNA_stomach_cancer",
            "ovarian_cancer": "cancer_RNA_ovarian_cancer",
        }

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        gene_name = arguments.get("gene_name")
        tissue_type = arguments.get("tissue_type", "").lower()
        disease_name = arguments.get("disease_name", "").lower()

        if not gene_name:
            return {"status": "error", "error": "Parameter 'gene_name' is required"}
        if not disease_name:
            return {"status": "error", "error": "Parameter 'disease_name' is required"}

        # Normalise to underscore form to match cancer_columns dict keys
        # ("lung cancer" -> "lung_cancer"). Caller may pass either form.
        disease_norm = disease_name.replace(" ", "_")
        cancer_column = None
        for key, column in self.cancer_columns.items():
            if disease_norm == key or disease_norm in key or key in disease_norm:
                cancer_column = column
                break

        if not cancer_column:
            available_diseases = [
                k.replace("_", " ") for k in self.cancer_columns.keys()
            ]

            # Find similar disease names
            similar_diseases = []
            disease_keywords = disease_name.replace("_", " ").split()

            for valid_disease in available_diseases:
                for keyword in disease_keywords:
                    if (
                        keyword in valid_disease.lower()
                        or valid_disease.lower() in keyword
                    ):
                        similar_diseases.append(valid_disease)
                        break

            error_msg = f"Unsupported disease_name '{disease_name}'. "
            if similar_diseases:
                error_msg += f"Similar options: {similar_diseases[:3]}. "
            error_msg += f"All supported diseases: {available_diseases}"
            return {"status": "error", "error": error_msg}

        # Build request columns
        columns = f"g,gs,{cancer_column},rnatsm"
        result = self._make_api_request(gene_name, columns)

        if "error" in result:
            return result

        if not result:
            return {"status": "error", "error": "No expression data found"}

        # Extract the first matching gene data
        gene_data = result[0] if isinstance(result, list) and result else {}

        return {
            "status": "success",
            "data": {
                "gene_name": gene_name,
                "gene_symbol": gene_data.get("Gene", gene_name),
                "gene_synonym": gene_data.get("Gene synonym", ""),
                "tissue_type": tissue_type or "Not specified",
                "disease_name": disease_name,
                "disease_expression": gene_data.get(cancer_column, "N/A"),
                "healthy_expression": gene_data.get("RNA tissue specific nTPM", "N/A"),
                "expression_unit": "nTPM (normalized Transcripts Per Million)",
                "disease_vs_healthy": self._compare_disease_healthy(
                    gene_data.get(cancer_column),
                    gene_data.get("RNA tissue specific nTPM"),
                ),
            },
        }

    def _compare_disease_healthy(self, disease_expr, healthy_expr) -> str:
        """Compare expression difference between disease and healthy state"""
        try:
            disease_val = (
                float(disease_expr) if disease_expr and disease_expr != "N/A" else None
            )
            healthy_val = (
                float(healthy_expr) if healthy_expr and healthy_expr != "N/A" else None
            )

            if disease_val is None or healthy_val is None:
                return "Insufficient data for comparison"

            fold_change = disease_val / healthy_val if healthy_val > 0 else float("inf")

            if fold_change > 2:
                return f"Disease state expression upregulated {fold_change:.2f} fold"
            elif fold_change < 0.5:
                return (
                    f"Disease state expression downregulated {1 / fold_change:.2f} fold"
                )
            else:
                return f"Expression level relatively stable (fold change: {fold_change:.2f})"
        except Exception:
            return "Failed to calculate expression difference"


@register_tool("HPAGetBiologicalProcessTool")
class HPAGetBiologicalProcessTool(HPASearchApiTool):
    """
    Get biological process information related to a gene.
    Get specific biological processes a gene is involved in by gene name.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        # Predefined biological process list
        self.target_processes = [
            "Apoptosis",
            "Biological rhythms",
            "Cell cycle",
            "Host-virus interaction",
            "Necrosis",
            "Transcription",
            "Transcription regulation",
        ]

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        gene_name = arguments.get("gene_name")
        filter_processes = arguments.get("filter_processes", True)

        if not gene_name:
            return {"status": "error", "error": "Parameter 'gene_name' is required"}

        # Request biological process data for the gene
        columns = "g,gs,upbp"
        result = self._make_api_request(gene_name, columns)

        if "error" in result:
            return result

        if not result:
            return {"status": "error", "error": "No gene data found"}

        # Extract the first matching gene data
        gene_data = result[0] if isinstance(result, list) and result else {}

        # Parse biological processes
        biological_processes = gene_data.get("Biological process", "")
        if not biological_processes or biological_processes == "N/A":
            return {
                "status": "success",
                "data": {
                    "gene_name": gene_name,
                    "gene_symbol": gene_data.get("Gene", gene_name),
                    "gene_synonym": gene_data.get("Gene synonym", ""),
                    "biological_processes": [],
                    "target_processes_found": [],
                    "target_process_names": [],
                    "total_processes": 0,
                    "target_processes_count": 0,
                },
            }

        # Split and clean process list - handle both string and list formats
        processes_list = []
        if isinstance(biological_processes, list):
            processes_list = biological_processes
        elif isinstance(biological_processes, str):
            # Usually separated by semicolon or comma
            processes_list = [
                p.strip()
                for p in biological_processes.replace(";", ",").split(",")
                if p.strip()
            ]

        # Filter target processes
        target_found = []
        if filter_processes:
            for process in processes_list:
                for target in self.target_processes:
                    if target.lower() in process.lower():
                        target_found.append(
                            {"target_process": target, "full_description": process}
                        )

        return {
            "status": "success",
            "data": {
                "gene_name": gene_name,
                "gene_symbol": gene_data.get("Gene", gene_name),
                "gene_synonym": gene_data.get("Gene synonym", ""),
                "biological_processes": processes_list,
                "target_processes_found": target_found,
                "target_process_names": [tp["target_process"] for tp in target_found],
                "total_processes": len(processes_list),
                "target_processes_count": len(target_found),
            },
        }


@register_tool("HPAGetCancerPrognosticsTool")
class HPAGetCancerPrognosticsTool(HPAJsonApiTool):
    """
    Get prognostic value of a gene across various cancers.
    Uses the efficient JSON API to retrieve cancer prognostic data.
    """

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        ensembl_id = arguments.get("ensembl_id")
        if not ensembl_id:
            return {"status": "error", "error": "Parameter 'ensembl_id' is required"}

        data = self._make_api_request(ensembl_id)
        if "error" in data:
            return data

        # HPA assesses a fixed panel of cancer types per gene and reports a
        # p-value for every one of them, including the ones where expression
        # carries no survival signal. `prognostic_summary` only lists the
        # significant ones, so on its own it cannot distinguish "HPA tested this
        # cancer and found nothing" (a citable negative result) from "HPA has no
        # data for this cancer at all". Collect both sets and report the
        # denominator; the non-significant rows go in their own key so callers
        # iterating `prognostic_summary` see exactly what they saw before.
        prognostics = []
        non_prognostics = []
        for key, value in data.items():
            if key.startswith("Cancer prognostics") and isinstance(value, dict):
                if not value:
                    # Empty dict: cancer type not assessed for this gene.
                    continue
                cancer_type = key.replace("Cancer prognostics - ", "").strip()
                if value.get("is_prognostic"):
                    prognostics.append(
                        {
                            "cancer_type": cancer_type,
                            "prognostic_type": value.get("prognostic type", "Unknown"),
                            "p_value": value.get("p_val", "N/A"),
                            "is_prognostic": value.get("is_prognostic", False),
                        }
                    )
                else:
                    non_prognostics.append(
                        {
                            "cancer_type": cancer_type,
                            "prognostic_type": value.get("prognostic type", "") or None,
                            "p_value": value.get("p_val", "N/A"),
                            "is_prognostic": False,
                        }
                    )

        cancers_assessed_count = len(prognostics) + len(non_prognostics)

        return {
            "status": "success",
            "data": {
                "ensembl_id": ensembl_id,
                "gene": data.get("Gene", "Unknown"),
                "gene_synonym": data.get("Gene synonym", ""),
                "cancers_assessed_count": cancers_assessed_count,
                "prognostic_cancers_count": len(prognostics),
                "non_prognostic_cancers_count": len(non_prognostics),
                "prognostic_summary": (
                    prognostics
                    if prognostics
                    else "No significant prognostic value found in the analyzed cancers."
                ),
                "non_prognostic_summary": non_prognostics,
                "note": (
                    "Prognostic value indicates whether high/low expression of this gene "
                    "correlates with patient survival in specific cancer types. "
                    f"HPA assessed {cancers_assessed_count} cancer type(s) for this gene: "
                    f"{len(prognostics)} were significant and are listed in "
                    f"'prognostic_summary'; the remaining {len(non_prognostics)} were "
                    "assessed and found NOT prognostic and are listed with their p-values "
                    "in 'non_prognostic_summary'. A cancer type absent from BOTH lists was "
                    "not assessed by HPA for this gene."
                ),
            },
        }


@register_tool("HPAGetProteinInteractionsTool")
class HPAGetProteinInteractionsTool(HPASearchApiTool):
    """
    Get protein-protein interaction partners for a gene.
    Uses search API to retrieve interaction data.
    """

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        gene_name = arguments.get("gene_name")
        if not gene_name:
            return {"status": "error", "error": "Parameter 'gene_name' is required"}

        # Feature-68B-002: HPA 'ppi' column has been deprecated and returns no data.
        # Direct users to EBIProteinsInteractionsTool or STRING tools instead.
        return {
            "status": "error",
            "error": (
                "HPA protein-protein interaction data (ppi column) is no longer available "
                "via the HPA search API. Use EBIProteins_get_interactions with a UniProt "
                "accession, or STRING_get_interactions with a gene symbol instead."
            ),
        }


@register_tool("HPAGetRnaExpressionByTissueTool")
class HPAGetRnaExpressionByTissueTool(HPAJsonApiTool):
    """
    Query RNA expression levels for a gene in specific tissues.
    More precise than general tissue expression queries.
    """

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        ensembl_id = arguments.get("ensembl_id")
        tissue_names = arguments.get("tissue_names", [])

        if not ensembl_id:
            return {"status": "error", "error": "Parameter 'ensembl_id' is required"}
        if not tissue_names or not isinstance(tissue_names, list):
            # Provide helpful tissue name examples
            example_tissues = [
                "brain",
                "liver",
                "heart",
                "kidney",
                "lung",
                "pancreas",
                "skin",
                "muscle",
            ]
            return {
                "status": "error",
                "error": f"Parameter 'tissue_names' is required and must be a list. Example: {example_tissues}",
            }

        data = self._make_api_request(ensembl_id)
        if "error" in data:
            return data

        # "RNA tissue specific nTPM" is HPA's tissue-*enrichment* summary: it is
        # populated only with the handful of tissues a gene is classified as
        # enriched in, not the full ~50-tissue nTPM panel. Reading it alone made
        # every non-enriched tissue look like missing data -- MAPT/'cerebral
        # cortex' returned "No data" while HPA holds 147.9 nTPM for it. Query the
        # per-tissue `t_RNA_<tissue>` columns instead (the same correction
        # already applied to HPAGetRnaExpressionBySourceTool in Fix-R4A-2) and
        # keep the enrichment summary only as a fallback.
        rna_data = data.get("RNA tissue specific nTPM", {})
        if not isinstance(rna_data, dict):
            rna_data = {}
        available_tissues = list(rna_data.keys())

        panel = self._fetch_tissue_panel(ensembl_id, tissue_names)

        expression_results = {}
        for tissue in tissue_names:
            hit = panel.get(tissue)
            if hit is not None:
                value, label = hit
                # HPA's own column header is the source of truth for both the
                # matched tissue and the unit -- never synthesise it from the
                # caller's string, which is how 'skin' used to be reported as
                # "Tissue RNA - skin [nTPM]", a column HPA does not have.
                matched = label.split(" RNA - ", 1)[-1]
                matched = re.sub(r"\s*\[[^\[\]]*\]\s*$", "", matched)
                entry = {
                    "matched_tissue": matched,
                    "expression_value": value,
                    "expression_level": self._categorize_expression(value),
                    "expression_unit": hpa_unit_from_column_label(label, "nTPM"),
                    "source_field": label,
                }
                if hpa_slug(matched) != hpa_slug(tissue):
                    column = HPA_TISSUE_COLUMN_ALIASES.get(
                        hpa_slug(tissue), [hpa_slug(matched)]
                    )[0]
                    entry["note"] = (
                        f"HPA publishes this tissue as '{matched}', not "
                        f"'{tissue}'; the value is from its 't_RNA_{column}' column."
                    )
                expression_results[tissue] = entry
                continue

            unavailable = HPA_UNAVAILABLE_SOURCES["tissue"].get(hpa_slug(tissue))
            if unavailable:
                expression_results[tissue] = {
                    "matched_tissue": "Not found",
                    "expression_value": "N/A",
                    "expression_level": "No data",
                    "note": unavailable,
                }
                continue

            # Fall back to the enrichment summary (case-insensitive substring
            # match), which is all HPA's JSON record carries.
            found_tissue = None
            for available_tissue in available_tissues:
                if (
                    tissue.lower() in available_tissue.lower()
                    or available_tissue.lower() in tissue.lower()
                ):
                    found_tissue = available_tissue
                    break

            if found_tissue:
                expression_results[tissue] = {
                    "matched_tissue": found_tissue,
                    "expression_value": rna_data[found_tissue],
                    "expression_level": self._categorize_expression(
                        rna_data[found_tissue]
                    ),
                    "source_field": "RNA tissue specific nTPM (enrichment summary)",
                }
            else:
                # HPA silently drops unknown columns, so an absent column means
                # the tissue name is not one HPA publishes -- report that as a
                # naming problem rather than as "this gene is not expressed".
                expression_results[tissue] = {
                    "matched_tissue": "Not found",
                    "expression_value": "N/A",
                    "expression_level": "No data",
                    "note": (
                        f"'{tissue}' did not match an HPA tissue column "
                        f"(t_RNA_{self._tissue_column_suffix(tissue)}). This means the "
                        "tissue name is unrecognized, not that the gene lacks "
                        "expression. HPA's consensus tissues: "
                        f"{sorted(HPA_TISSUE_RNA_COLUMNS)}."
                    ),
                }

        result = {
            "ensembl_id": ensembl_id,
            "gene": data.get("Gene", "Unknown"),
            "gene_synonym": data.get("Gene synonym", ""),
            "expression_unit": "nTPM (normalized Transcripts Per Million)",
            "queried_tissues": tissue_names,
            "tissue_expression": expression_results,
            "enriched_tissues": available_tissues,
        }
        # Each row surrounds `expression_level` with real HPA provenance
        # (`source_field` is a literal HPA column name), so the band needs
        # marking -- but there is one row per queried tissue, so state the
        # cut-offs once here rather than repeating them on every row. Omitted
        # when no row was banded at all ("No data" rows are already honest).
        basis = next(
            (
                b
                for b in (
                    HPA_EXPRESSION_BANDING_TITLE.basis_for(
                        row.get("expression_level"), "nTPM"
                    )
                    for row in expression_results.values()
                )
                if b
            ),
            None,
        )
        if basis:
            result["expression_level_basis"] = basis

        return {"status": "success", "data": result}

    @staticmethod
    def _tissue_column_suffix(tissue: str) -> str:
        """Convert a human tissue name to HPA's column suffix form."""
        return hpa_slug(tissue)

    @staticmethod
    def _tissue_column_candidates(tissue: str) -> list[str]:
        """Resolve a caller's tissue name to real HPA `t_RNA_` column suffixes.

        Fix-R31: the slugified name is NOT always a column. HPA publishes
        'skin' as `t_RNA_skin_1`, 'stomach' as `t_RNA_stomach_1` and
        'endometrium' as `t_RNA_endometrium_1`; `t_RNA_skin` etc. are silently
        dropped, which the tool then misreported as an unrecognized tissue
        name. Consult the verified catalogue first, and still try the raw slug
        so a column HPA adds later keeps working without a code change.
        """
        slug = hpa_slug(tissue)
        candidates = list(HPA_TISSUE_COLUMN_ALIASES.get(slug, []))
        if slug and slug not in candidates:
            candidates.append(slug)
        return candidates

    def _fetch_tissue_panel(
        self, ensembl_id: str, tissue_names: List[str]
    ) -> Dict[str, Any]:
        """Fetch per-tissue nTPM values via HPA's search API `t_RNA_<tissue>` columns.

        HPA drops columns it does not recognize instead of erroring, so a tissue
        missing from the response is an unknown tissue name. Returns a mapping of
        the caller's original tissue strings to (value, HPA column header).
        """
        candidates = {t: self._tissue_column_candidates(t) for t in tissue_names}
        columns = ["g", "eg"]
        for suffixes in candidates.values():
            for suffix in suffixes:
                column = f"t_RNA_{suffix}"
                if column not in columns:
                    columns.append(column)
        params = {
            "search": ensembl_id,
            "format": "json",
            "columns": ",".join(columns),
            "compress": "no",
        }
        try:
            resp = requests.get(HPA_SEARCH_API, params=params, timeout=self.timeout)
            if resp.status_code != 200:
                return {}
            rows = resp.json()
        except (requests.RequestException, ValueError):
            return {}
        if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
            return {}

        row = rows[0]
        # HPA labels the returned columns "Tissue RNA - <tissue> [nTPM]".
        by_suffix = {}
        for key, value in row.items():
            match = re.match(r"^Tissue RNA - (.+?) \[[^\[\]]+\]$", key)
            if match:
                by_suffix[hpa_slug(match.group(1))] = (value, key)

        panel = {}
        for tissue, suffixes in candidates.items():
            for suffix in suffixes:
                hit = by_suffix.get(suffix)
                if hit and hit[0] not in (None, ""):
                    panel[tissue] = hit
                    break
        return panel

    def _categorize_expression(self, expr_value) -> str:
        """Categorize expression level."""
        return HPA_EXPRESSION_BANDING_TITLE.categorize(expr_value)


@register_tool("HPAGetContextualBiologicalProcessTool")
class HPAGetContextualBiologicalProcessTool(BaseTool):
    """
    Analyze a gene's biological processes in the context of specific tissue or cell line.
    Enhanced with intelligent context validation and recommendation.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        # Define all valid context options
        self.valid_contexts = {
            "tissues": [
                "adipose_tissue",
                "adrenal_gland",
                "appendix",
                "bone_marrow",
                "brain",
                "breast",
                "bronchus",
                "cerebellum",
                "cerebral_cortex",
                "cervix",
                "colon",
                "duodenum",
                "endometrium",
                "esophagus",
                "gallbladder",
                "heart_muscle",
                "kidney",
                "liver",
                "lung",
                "lymph_node",
                "ovary",
                "pancreas",
                "placenta",
                "prostate",
                "rectum",
                "salivary_gland",
                "skeletal_muscle",
                "skin",
                "small_intestine",
                "spleen",
                "stomach",
                "testis",
                "thymus",
                "thyroid_gland",
                "urinary_bladder",
                "vagina",
            ],
            "cell_lines": [
                "hela",
                "mcf7",
                "a549",
                "hepg2",
                "jurkat",
                "pc3",
                "rh30",
                "siha",
                "u251",
            ],
            "blood_cells": [
                "t_cell",
                "b_cell",
                "nk_cell",
                "monocyte",
                "neutrophil",
                "eosinophil",
            ],
            "brain_regions": [
                "cerebellum",
                "cerebral_cortex",
                "hippocampus",
                "hypothalamus",
                "amygdala",
            ],
        }

    def _validate_context(self, context_name: str) -> Dict[str, Any]:
        """Validate context_name and provide intelligent recommendations"""
        context_lower = context_name.lower().replace(" ", "_").replace("-", "_")

        # Check all valid contexts
        all_valid = []
        for category, contexts in self.valid_contexts.items():
            all_valid.extend(contexts)
            if context_lower in contexts:
                return {"valid": True, "category": category}

        # Find similar contexts (fuzzy matching)
        similar_contexts = []
        context_keywords = context_lower.split("_")

        for valid_context in all_valid:
            for keyword in context_keywords:
                if keyword in valid_context.lower() or valid_context.lower() in keyword:
                    similar_contexts.append(valid_context)
                    break

        return {
            "valid": False,
            "input": context_name,
            "similar_suggestions": similar_contexts[:5],  # Top 5 suggestions
            "all_tissues": self.valid_contexts["tissues"][:10],  # First 10 tissues
            "all_cell_lines": self.valid_contexts["cell_lines"],
            "total_available": len(all_valid),
        }

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        gene_name = arguments.get("gene_name")
        context_name = arguments.get("context_name")

        if not gene_name:
            return {"status": "error", "error": "Parameter 'gene_name' is required"}
        if not context_name:
            return {"status": "error", "error": "Parameter 'context_name' is required"}

        # Validate context_name and provide recommendations if invalid
        validation = self._validate_context(context_name)
        if not validation["valid"]:
            error_msg = f"Invalid context_name '{validation['input']}'. "
            if validation["similar_suggestions"]:
                error_msg += f"Similar options: {validation['similar_suggestions']}. "
            error_msg += f"Available tissues: {validation['all_tissues']}... "
            error_msg += f"Available cell lines: {validation['all_cell_lines']}. "
            error_msg += f"Total {validation['total_available']} contexts available."
            return {"status": "error", "error": error_msg}

        try:
            # Step 1: Get gene basic info and Ensembl ID
            search_api = HPASearchApiTool({})
            search_result = search_api._make_api_request(gene_name, "g,gs,eg,upbp")

            if "error" in search_result or not search_result:
                return {
                    "status": "error",
                    "error": f"Could not find gene information for '{gene_name}'",
                }

            gene_data = (
                search_result[0] if isinstance(search_result, list) else search_result
            )
            ensembl_id = gene_data.get("Ensembl", "")

            if not ensembl_id:
                return {
                    "status": "error",
                    "error": f"Could not find Ensembl ID for gene '{gene_name}'",
                }

            # Step 2: Get biological processes
            biological_processes = gene_data.get("Biological process", "")
            processes_list = []
            if biological_processes and biological_processes != "N/A":
                if isinstance(biological_processes, list):
                    processes_list = biological_processes
                elif isinstance(biological_processes, str):
                    processes_list = [
                        p.strip()
                        for p in biological_processes.replace(";", ",").split(",")
                        if p.strip()
                    ]

            # Step 3: Get expression in context with improved error handling
            json_api = HPAJsonApiTool({})
            json_data = json_api._make_api_request(ensembl_id)

            expression_value = "N/A"
            expression_level = "not expressed"
            context_type = (
                validation["category"].replace("_", " ").rstrip("s")
            )  # "tissues" -> "tissue"

            if "error" not in json_data and json_data:
                # FIXED: Check if rna_data is not None before calling .keys()
                rna_data = json_data.get("RNA tissue specific nTPM")
                if rna_data and isinstance(rna_data, dict):
                    # Try to find matching tissue
                    for tissue_key in rna_data.keys():
                        if (
                            context_name.lower() in tissue_key.lower()
                            or tissue_key.lower() in context_name.lower()
                        ):
                            expression_value = rna_data[tissue_key]
                            break

                # If not found in tissues and it's a cell line, try cell line data
                if expression_value == "N/A" and validation["category"] == "cell_lines":
                    context_type = "cell line"
                    cell_line_columns = {
                        "hela": "cell_RNA_hela",
                        "mcf7": "cell_RNA_mcf7",
                        "a549": "cell_RNA_a549",
                        "hepg2": "cell_RNA_hepg2",
                    }

                    cell_column = cell_line_columns.get(context_name.lower())
                    if cell_column:
                        cell_result = search_api._make_api_request(
                            gene_name, f"g,{cell_column}"
                        )
                        if "error" not in cell_result and cell_result:
                            expression_value = cell_result[0].get(cell_column, "N/A")

            # Categorize expression level. Bands live in
            # HPA_CONTEXTUAL_EXPRESSION_BANDING so the cut-offs disclosed below
            # cannot drift from the ones applied here. A missing value still
            # bands as 0 rather than as 'unclear', which is what it did before.
            expression_level = HPA_CONTEXTUAL_EXPRESSION_BANDING.categorize(
                0 if expression_value == "N/A" else expression_value
            )

            # Generate contextual conclusion
            relevance = (
                "may be functionally relevant"
                if "expressed" in expression_level and "not" not in expression_level
                else "is likely not functionally relevant"
            )

            conclusion = f"Gene {gene_name} is involved in {len(processes_list)} biological processes. It is {expression_level} in {context_name} ({expression_value} nTPM), suggesting its functional roles {relevance} in this {context_type} context."

            result = {
                "gene": gene_data.get("Gene", gene_name),
                "gene_synonym": gene_data.get("Gene synonym", ""),
                "ensembl_id": ensembl_id,
                "context": context_name,
                "context_type": context_type,
                "context_category": validation["category"],
                "expression_in_context": f"{expression_value} nTPM",
                "expression_level": expression_level,
                "total_biological_processes": len(processes_list),
                "biological_processes": (
                    processes_list[:10] if len(processes_list) > 10 else processes_list
                ),
                "contextual_conclusion": conclusion,
                "functional_relevance": relevance,
            }
            # `expression_in_context` and `biological_processes` are HPA's;
            # `expression_level` is ours, and here it also drives
            # `functional_relevance` and the `contextual_conclusion` sentence,
            # so the cut-offs behind that verdict have to travel with it.
            basis = HPA_CONTEXTUAL_EXPRESSION_BANDING.basis_for(
                expression_level, "nTPM"
            )
            if basis:
                result["expression_level_basis"] = basis
            return {"status": "success", "data": result}

        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to perform contextual analysis: {str(e)}",
            }


# --- Keep existing comprehensive gene details tool for images ---


@register_tool("HPAGetGenePageDetailsTool")
class HPAGetGenePageDetailsTool(HPAXmlApiTool):
    """
    Get detailed information about a gene page, including images, protein expression, antibody data, etc.
    Get the most comprehensive data by parsing HPA's single gene XML endpoint.
    Enhanced version with improved image extraction and comprehensive data parsing based on optimization plan.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        ensembl_id = arguments.get("ensembl_id")
        include_images = arguments.get("include_images", True)
        include_antibodies = arguments.get("include_antibodies", True)
        include_expression = arguments.get("include_expression", True)

        if not ensembl_id:
            return {"status": "error", "error": "Parameter 'ensembl_id' is required"}

        try:
            root = self._make_api_request(ensembl_id)
            parsed = self._parse_gene_xml(
                root, ensembl_id, include_images, include_antibodies, include_expression
            )
            return {"status": "success", "data": parsed}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _parse_gene_xml(
        self,
        root: ET.Element,
        ensembl_id: str,
        include_images: bool,
        include_antibodies: bool,
        include_expression: bool,
    ) -> Dict[str, Any]:
        """Parse gene XML data comprehensively based on actual HPA XML schema"""
        result = {
            "ensembl_id": ensembl_id,
            "gene_name": "",
            "gene_description": "",
            "chromosome_location": "",
            "uniprot_ids": [],
            "summary": {},
        }

        # Extract basic gene information from entry element
        entry_elem = root.find(".//entry")
        if entry_elem is not None:
            # Gene name
            name_elem = entry_elem.find("name")
            if name_elem is not None:
                result["gene_name"] = name_elem.text or ""

            # Gene synonyms
            synonyms = []
            for synonym_elem in entry_elem.findall("synonym"):
                if synonym_elem.text:
                    synonyms.append(synonym_elem.text)
            result["gene_synonyms"] = synonyms

            # Extract Uniprot IDs from identifier/xref elements
            identifier_elem = entry_elem.find("identifier")
            if identifier_elem is not None:
                for xref in identifier_elem.findall("xref"):
                    if xref.get("db") == "Uniprot/SWISSPROT":
                        result["uniprot_ids"].append(xref.get("id", ""))

            # Extract protein classes
            protein_classes = []
            protein_classes_elem = entry_elem.find("proteinClasses")
            if protein_classes_elem is not None:
                for pc in protein_classes_elem.findall("proteinClass"):
                    class_name = pc.get("name", "")
                    if class_name:
                        protein_classes.append(class_name)
            result["protein_classes"] = protein_classes

        # Extract image information with enhanced parsing
        if include_images:
            result["ihc_images"] = self._extract_ihc_images(root)
            result["if_images"] = self._extract_if_images(root)

        # Extract antibody information
        if include_antibodies:
            result["antibodies"] = self._extract_antibodies(root)

        # Extract expression information
        if include_expression:
            result["expression_summary"] = self._extract_expression_summary(root)
            result["tissue_expression"] = self._extract_tissue_expression(root)
            result["cell_line_expression"] = self._extract_cell_line_expression(root)

        # Extract summary statistics
        tissue_rows = result.get("tissue_expression", [])
        detected, assayed = self._count_tissues(tissue_rows)
        result["summary"] = {
            "total_antibodies": len(result.get("antibodies", [])),
            "total_ihc_images": len(result.get("ihc_images", [])),
            "total_if_images": len(result.get("if_images", [])),
            # Fix-R31: this used to be len(tissue_expression), i.e. the number
            # of assayed ROWS -- 184 for NCSTN, of which 135 carried no level
            # at all, 9 said "not detected", and the remainder repeated the
            # same tissue once per antibody ("Skin 1" appeared 4x). HPA
            # publishes ~44 consensus tissues, so the old number was
            # impossible on its face. Count distinct tissues whose IHC level
            # is actually detected.
            "tissues_with_expression": detected,
            "distinct_tissues_assayed": assayed,
            "tissue_expression_rows": len(tissue_rows),
            "cell_lines_with_expression": len(result.get("cell_line_expression", [])),
        }
        result["summary"]["summary_note"] = (
            "'tissues_with_expression' counts distinct tissues with a detected "
            "IHC expression level; rows with no level and rows scored "
            "'not detected' are excluded. 'tissue_expression_rows' is the raw "
            "row count of the tissue_expression array (one row per "
            "tissue x antibody)."
        )

        return result

    @staticmethod
    def _count_tissues(tissue_rows: list) -> tuple[int, int]:
        """Return (distinct tissues with detected expression, distinct assayed).

        `tissue_expression` holds one row per tissue x antibody, many of them
        with a blank or "not detected" level, so its length is neither a
        tissue count nor an expression count.
        """
        not_detected = {"", "not detected", "none", "negative", "n/a", "undetected"}
        detected, assayed = set(), set()
        for row in tissue_rows or []:
            if not isinstance(row, dict):
                continue
            name = str(row.get("tissue_name") or "").strip().lower()
            if not name:
                continue
            assayed.add(name)
            level = str(row.get("expression_level") or "").strip().lower()
            # Levels arrive as "<type>: <level>", e.g. "expression: medium".
            level = level.rsplit(":", 1)[-1].strip()
            if level and level not in not_detected:
                detected.add(name)
        return len(detected), len(assayed)

    def _extract_ihc_images(self, root: ET.Element) -> List[Dict[str, Any]]:
        """Extract tissue immunohistochemistry (IHC) images based on actual HPA XML structure"""
        images = []

        # Find tissueExpression elements which contain IHC images
        for tissue_expr in root.findall(".//tissueExpression"):
            # Extract selected images from tissueExpression
            for image_elem in tissue_expr.findall(".//image"):
                image_type = image_elem.get("imageType", "")
                if image_type == "selected":
                    tissue_elem = image_elem.find("tissue")
                    image_url_elem = image_elem.find("imageUrl")

                    if tissue_elem is not None and image_url_elem is not None:
                        tissue_name = tissue_elem.text or ""
                        organ = tissue_elem.get("organ", "")
                        ontology_terms = tissue_elem.get("ontologyTerms", "")
                        image_url = image_url_elem.text or ""

                        images.append(
                            {
                                "image_type": "Immunohistochemistry",
                                "tissue_name": tissue_name,
                                "organ": organ,
                                "ontology_terms": ontology_terms,
                                "image_url": image_url,
                                "selected": True,
                            }
                        )

        return images

    def _extract_if_images(self, root: ET.Element) -> List[Dict[str, Any]]:
        """Extract subcellular immunofluorescence (IF) images based on actual HPA XML structure"""
        images = []

        # Look for subcellular expression data (IF images are typically in subcellular sections)
        for subcell_expr in root.findall(".//subcellularExpression"):
            # Extract subcellular location images
            for image_elem in subcell_expr.findall(".//image"):
                image_type = image_elem.get("imageType", "")
                if image_type == "selected":
                    location_elem = image_elem.find("location")
                    image_url_elem = image_elem.find("imageUrl")

                    if location_elem is not None and image_url_elem is not None:
                        location_name = location_elem.text or ""
                        image_url = image_url_elem.text or ""

                        images.append(
                            {
                                "image_type": "Immunofluorescence",
                                "subcellular_location": location_name,
                                "image_url": image_url,
                                "selected": True,
                            }
                        )

        return images

    def _extract_antibodies(self, root: ET.Element) -> List[Dict[str, Any]]:
        """Extract antibody information from actual HPA XML structure"""
        antibodies_data = []

        # Look for antibody references in various expression sections
        antibody_ids = set()

        # Look for antibody references in tissue expression
        for tissue_expr in root.findall(".//tissueExpression"):
            for elem in tissue_expr.iter():
                if "antibody" in elem.tag.lower() or elem.get("antibody"):
                    antibody_id = elem.get("antibody") or elem.text
                    if antibody_id:
                        antibody_ids.add(antibody_id)

        # Create basic antibody info for found IDs
        for antibody_id in antibody_ids:
            antibodies_data.append(
                {
                    "antibody_id": antibody_id,
                    "source": "HPA",
                    "applications": ["IHC", "IF"],
                    "validation_status": "Available",
                }
            )

        # If no specific antibody IDs found, create a placeholder
        if not antibodies_data:
            antibodies_data.append(
                {
                    "antibody_id": "HPA_antibody",
                    "source": "HPA",
                    "applications": ["IHC", "IF"],
                    "validation_status": "Available",
                }
            )

        return antibodies_data

    def _extract_expression_summary(self, root: ET.Element) -> Dict[str, Any]:
        """Extract expression summary information from actual HPA XML structure"""
        summary = {
            "tissue_specificity": "",
            "subcellular_location": [],
            "protein_class": [],
            "predicted_location": "",
            "tissue_expression_summary": "",
            "subcellular_expression_summary": "",
        }

        # Extract predicted location
        predicted_location_elem = root.find(".//predictedLocation")
        if predicted_location_elem is not None:
            summary["predicted_location"] = predicted_location_elem.text or ""

        # Extract tissue expression summary
        tissue_expr_elem = root.find(".//tissueExpression")
        if tissue_expr_elem is not None:
            tissue_summary_elem = tissue_expr_elem.find("summary")
            if tissue_summary_elem is not None:
                summary["tissue_expression_summary"] = tissue_summary_elem.text or ""

        # Extract subcellular expression summary
        subcell_expr_elem = root.find(".//subcellularExpression")
        if subcell_expr_elem is not None:
            subcell_summary_elem = subcell_expr_elem.find("summary")
            if subcell_summary_elem is not None:
                summary["subcellular_expression_summary"] = (
                    subcell_summary_elem.text or ""
                )

        return summary

    def _extract_tissue_expression(self, root: ET.Element) -> List[Dict[str, Any]]:
        """Extract detailed tissue expression data from actual HPA XML structure"""
        tissue_data = []

        # Extract from tissueExpression data elements
        for tissue_expr in root.findall(".//tissueExpression"):
            for data_elem in tissue_expr.findall(".//data"):
                tissue_elem = data_elem.find("tissue")
                level_elem = data_elem.find("level")

                if tissue_elem is not None:
                    tissue_info = {
                        "tissue_name": tissue_elem.text or "",
                        "organ": tissue_elem.get("organ", ""),
                        "expression_level": "",
                    }

                    if level_elem is not None:
                        tissue_info["expression_level"] = (
                            level_elem.get("type", "") + ": " + (level_elem.text or "")
                        )

                    tissue_data.append(tissue_info)

        return tissue_data

    def _extract_cell_line_expression(self, root: ET.Element) -> List[Dict[str, Any]]:
        """Extract cell line expression data from actual HPA XML structure"""
        cell_line_data = []

        # Look for cell line expression in subcellular expression
        for subcell_expr in root.findall(".//subcellularExpression"):
            for data_elem in subcell_expr.findall(".//data"):
                cell_line_elem = data_elem.find("cellLine")
                if cell_line_elem is not None:
                    cell_info = {
                        "cell_line_name": cell_line_elem.get("name", "")
                        or (cell_line_elem.text or ""),
                        "expression_data": [],
                    }

                    if cell_info["expression_data"]:
                        cell_line_data.append(cell_info)

        return cell_line_data


# --- Legacy/Compatibility Tools ---


@register_tool("HPAGetGeneJSONTool")
class HPAGetGeneJSONTool(HPAJsonApiTool):
    """
    Enhanced legacy tool - Get basic gene information using Ensembl Gene ID.
    Now uses the efficient JSON API instead of search API.
    """

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        ensembl_id = arguments.get("ensembl_id")
        if not ensembl_id:
            return {"status": "error", "error": "Parameter 'ensembl_id' is required"}

        # Use JSON API to get comprehensive information
        data = self._make_api_request(ensembl_id)

        if "error" in data:
            return data

        # Convert to response similar to original JSON format for compatibility
        return {
            "Ensembl": ensembl_id,
            "Gene": data.get("Gene", ""),
            "Gene synonym": data.get("Gene synonym", ""),
            "Uniprot": data.get("Uniprot", ""),
            "Biological process": data.get("Biological process", ""),
            "RNA tissue specific nTPM": data.get("RNA tissue specific nTPM", ""),
        }


@register_tool("HPAGetGeneXMLTool")
class HPAGetGeneXMLTool(HPASearchApiTool):
    """
    Legacy tool - Get gene TSV format data (alternative to XML).
    """

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        ensembl_id = arguments.get("ensembl_id")
        if not ensembl_id:
            return {"status": "error", "error": "Parameter 'ensembl_id' is required"}

        # Use TSV format to get detailed data
        columns = "g,gs,up,upbp,rnatsm,cell_RNA_a549,cell_RNA_hela"
        result = self._make_api_request(ensembl_id, columns, format_type="tsv")

        if "error" in result:
            return result

        return {"tsv_data": result.get("tsv_data", "")}
