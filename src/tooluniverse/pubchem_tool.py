# pubchem_tool.py

import requests
import re
from .base_tool import BaseTool
from .tool_registry import register_tool

# Base URL for PubChem PUG-REST
PUBCHEM_BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

# Base URL for PubChem PUG-View
PUBCHEM_PUGVIEW_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug_view"

# PubChem's /xrefs/{type} endpoint accepts only this fixed vocabulary.
# Database-specific identifiers (ChEBI, KEGG, ChEMBL, InChIKey, ...) are NOT
# xref types — they are embedded inside the 'RegistryID' values — so passing
# them yields an opaque HTTP 400 "Invalid xrefs type". We validate up front.
PUBCHEM_XREF_TYPES = frozenset(
    {
        "RegistryID",
        "RN",
        "PubMedID",
        "MMDBID",
        "ProteinGI",
        "NucleotideGI",
        "TaxonomyID",
        "MIMID",
        "GeneID",
        "ProbeID",
        "PatentID",
        "SourceName",
        "SourceCategory",
        "DBURL",
        "SBURL",
    }
)


@register_tool("PubChemRESTTool")
class PubChemRESTTool(BaseTool):
    """
    Generic PubChem PUG-REST tool class.
    Directly concatenates URL from the fields.endpoint template and sends requests to PubChem PUG-REST.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        # Read endpoint template directly from fields config
        self.endpoint_template = tool_config["fields"]["endpoint"]
        # input_description and output_description might not be used, but kept for LLM reference
        self.input_description = tool_config["fields"].get("input_description", "")
        self.output_description = tool_config["fields"].get("output_description", "")
        # If property_list exists, it will be used to replace {property_list} placeholder
        self.property_list = tool_config["fields"].get("property_list", None)
        # Parameter schema (properties may include required field)
        self.param_schema = tool_config["parameter"]["properties"]
        self.use_pugview = tool_config["fields"].get("use_pugview", False)
        self.output_format = tool_config["fields"].get("return_format", None)
        # When set, run() parses the raw PC_Substances record into a flat
        # depositor-level summary and (optionally) merges linked compound CIDs,
        # rather than returning the raw PUG payload. Keyed off a fields flag so
        # this stays within the existing PubChemRESTTool type — no new class.
        self.substance_record = tool_config["fields"].get("substance_record", False)

    def _build_url(self, arguments: dict) -> str:
        """
        Use regex to replace all {placeholder} in endpoint_template to generate complete URL path.
        For example endpoint_template="/compound/cid/{cid}/property/{property_list}/JSON"
        arguments={"cid":2244}, property_list=["MolecularWeight","IUPACName"]
        → "/compound/cid/2244/property/MolecularWeight,IUPACName/JSON"
        Finally returns "https://pubchem.ncbi.nlm.nih.gov/rest/pug" + concatenated path.
        """
        url_path = self.endpoint_template

        # Replace {property_list}. Prefer a caller-supplied `properties`
        # argument over the fixed config default so the caller can choose
        # which properties to fetch — the tool is "get_compound_properties"
        # but previously ignored the requested set and always returned the
        # three configured defaults.
        if "{property_list}" in url_path:
            user_props = arguments.get("properties")
            if user_props:
                prop_list = (
                    user_props
                    if isinstance(user_props, list)
                    else [p.strip() for p in str(user_props).split(",") if p.strip()]
                )
            else:
                prop_list = self.property_list or []
            if prop_list:
                url_path = url_path.replace(
                    "{property_list}", ",".join(map(str, prop_list))
                )

        # Find all placeholders {xxx} in template
        placeholders = re.findall(r"\{([^{}]+)\}", url_path)
        for ph in placeholders:
            if ph not in arguments:
                # If a placeholder cannot find corresponding value in arguments, report error
                raise ValueError(
                    f"Missing required parameter '{ph}' to replace placeholder in URL."
                )
            val = arguments[ph]
            # If input value is a list, join with commas
            if isinstance(val, list):
                val_str = ",".join(map(str, val))
            else:
                val_str = str(val)
            url_path = url_path.replace(f"{{{ph}}}", val_str)

        # Handle xref_types parameter. Validate against PubChem's fixed
        # vocabulary first so an invalid type returns an actionable error
        # instead of an opaque HTTP 400 "Invalid xrefs type".
        if "xref_types" in arguments:
            requested = arguments["xref_types"]
            if isinstance(requested, str):
                requested = [t.strip() for t in requested.split(",") if t.strip()]
            invalid = [t for t in requested if t not in PUBCHEM_XREF_TYPES]
            if invalid:
                raise ValueError(
                    f"Invalid xref_types {invalid}. PubChem /xrefs accepts only: "
                    f"{', '.join(sorted(PUBCHEM_XREF_TYPES))}. Database "
                    "cross-references such as ChEBI, KEGG, ChEMBL and InChIKey "
                    "are not separate xref types — they appear inside the "
                    "'RegistryID' values, so use xref_types=['RegistryID']."
                )
            url_path = url_path.replace("{xref_list}", ",".join(requested))

        # Finally combine into complete URL
        if self.use_pugview:
            full_url = PUBCHEM_PUGVIEW_URL + url_path
        else:
            full_url = PUBCHEM_BASE_URL + url_path

        # Handle special parameters
        if "threshold" in arguments:
            # Convert 0-1 threshold to 0-100 integer
            threshold = float(arguments["threshold"])
            if 0 <= threshold <= 1:
                threshold = int(threshold * 100)
            # Add threshold parameter to URL
            if "?" in full_url:
                full_url += f"&Threshold={threshold}"
            else:
                full_url += f"?Threshold={threshold}"

        return full_url

    @staticmethod
    def _parse_substance_payload(payload: dict) -> dict:
        """Flatten one raw PC_Substances entry into a depositor-level summary.

        Returns the parsed record dict (without linked CIDs), or None when the
        payload contains no substance entry.
        """
        substances = (payload or {}).get("PC_Substances") or []
        if not substances:
            return None
        rec = substances[0]

        sid = (rec.get("sid") or {}).get("id")

        # source.db.name is the depositor's source identifier; source_id.str /
        # source_id.id is that depositor's own record id for the substance.
        db = (rec.get("source") or {}).get("db") or {}
        source_id_obj = db.get("source_id") or {}
        source_id = source_id_obj.get("str")
        if source_id is None:
            source_id = source_id_obj.get("id")

        # xref entries are heterogeneous (regid / patent / dburl / ...); surface
        # them as-is plus a flat list of registry ids for convenience.
        xrefs = rec.get("xref") or []
        registry_ids = [
            x["regid"] for x in xrefs if isinstance(x, dict) and "regid" in x
        ]

        return {
            "sid": sid,
            "source_name": db.get("name"),
            "source_id": source_id,
            "synonyms": rec.get("synonyms") or [],
            "comment": rec.get("comment") or [],
            "registry_ids": registry_ids,
            "xrefs": xrefs,
        }

    def _run_substance_record(self, arguments: dict) -> dict:
        """Fetch and parse a PubChem SUBSTANCE (SID) record, merging linked CIDs."""
        sid = arguments.get("sid")
        if sid is None or str(sid).strip() == "":
            return {"status": "error", "error": "Parameter 'sid' is required."}
        sid = str(sid).strip()
        if not sid.isdigit():
            return {
                "status": "error",
                "error": f"Invalid 'sid' {sid!r}: a PubChem SID must be a positive integer.",
            }

        base = f"{PUBCHEM_BASE_URL}/substance/sid/{sid}"

        # 1. Main substance record
        try:
            resp = requests.get(f"{base}/JSON", timeout=30)
        except requests.Timeout:
            return {
                "status": "error",
                "error": "Request to PubChem PUG-REST timed out, retry later.",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to request PubChem PUG-REST: {str(e)}",
            }

        if resp.status_code == 404:
            return {
                "status": "success",
                "found": False,
                "data": {"sid": sid},
                "metadata": {
                    "note": f"No PubChem substance record found for SID {sid}."
                },
            }
        if resp.status_code != 200:
            detail = resp.text
            try:
                fault = resp.json().get("Fault")
                if fault:
                    detail = fault.get("Message", detail)
            except Exception:
                pass
            return {
                "status": "error",
                "error": f"PubChem API returned HTTP {resp.status_code}",
                "detail": detail,
            }

        try:
            payload = resp.json()
        except ValueError:
            return {
                "status": "error",
                "error": "PubChem substance response could not be parsed as JSON.",
            }

        record = self._parse_substance_payload(payload)
        if record is None:
            return {
                "status": "success",
                "found": False,
                "data": {"sid": sid},
                "metadata": {
                    "note": f"No PubChem substance record found for SID {sid}."
                },
            }

        # 2. Linked compound CIDs (best-effort — never fail the whole call on this)
        linked_cids = []
        try:
            cresp = requests.get(f"{base}/cids/JSON", timeout=30)
            if cresp.status_code == 200:
                info = cresp.json().get("InformationList", {}).get("Information") or [
                    {}
                ]
                linked_cids = info[0].get("CID") or []
        except Exception:
            linked_cids = []
        record["linked_cids"] = linked_cids

        return {
            "status": "success",
            "found": True,
            "data": record,
            "metadata": {
                "sid": int(sid),
                "source_url": f"{base}/JSON",
                "linked_cid_count": len(linked_cids),
            },
        }

    def run(self, arguments: dict):
        # Substance (SID, depositor-level) record lookup is handled separately:
        # it parses the raw PC_Substances payload and merges linked CIDs.
        if self.substance_record:
            return self._run_substance_record(arguments)

        # compound_name alias for name (more intuitive param name)
        if "name" not in arguments and "compound_name" in arguments:
            arguments["name"] = arguments["compound_name"]

        # vendor alias for source (reverse-sourcing tool uses {source} in its URL
        # template; 'vendor' is the more intuitive parameter name for callers).
        if "source" not in arguments and "vendor" in arguments:
            arguments["source"] = arguments["vendor"]

        # 1. Validate required parameters
        for key, prop in self.param_schema.items():
            if prop.get("required", False) and key not in arguments:
                return {"status": "error", "error": f"Parameter '{key}' is required."}

        # 2. Build URL
        try:
            url = self._build_url(arguments)
        except ValueError as e:
            return {"status": "error", "error": str(e)}

        # 3. Send HTTP GET request
        try:
            # Increase timeout to 30 seconds and add MaxRecords parameter to limit results
            if "fastsubstructure" in url or "fastsimilarity" in url:
                max_records = arguments.get("max_results", 10)
                if "?" in url:
                    url += f"&MaxRecords={max_records}"
                else:
                    url += f"?MaxRecords={max_records}"

            resp = requests.get(url, timeout=30)
        except requests.Timeout:
            return {
                "status": "error",
                "error": "Request to PubChem PUG-REST timed out, try reducing query scope or retry later.",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to request PubChem PUG-REST: {str(e)}",
            }

        # 4. Check HTTP status code
        if resp.status_code != 200:
            error_detail = resp.text
            try:
                error_json = resp.json()
                if "Fault" in error_json:
                    error_detail = error_json["Fault"].get("Message", error_detail)
            except Exception:
                pass
            return {
                "status": "error",
                "error": f"PubChem API returned HTTP {resp.status_code}",
                "detail": error_detail,
            }

        # 5. Determine return type based on URL suffix
        #    Look at the text after the last slash in endpoint_template, like "JSON","PNG","XML","TXT","CSV"
        if self.output_format:
            out_fmt = self.output_format
        else:
            # Strip query parameters before determining format
            endpoint_path = self.endpoint_template.split("?")[0]
            out_fmt = endpoint_path.strip("/").split("/")[-1].upper()

        if out_fmt == "JSON":
            try:
                return {"status": "success", "data": resp.json()}
            except ValueError:
                ct = resp.headers.get("content-type", "")
                return {
                    "status": "error",
                    "error": "Response content cannot be parsed as JSON.",
                    "content_type": ct,
                    "content": resp.text[:200],
                    "retryable": "text/html" in ct
                    or resp.text.lstrip().startswith("<"),
                }
        elif out_fmt in ["XML", "TXT", "CSV", "SDF"]:
            # These are all text formats
            return resp.text
        elif out_fmt in ["PNG", "SVG"]:
            # Return binary image
            return resp.content
        else:
            # Return text for other cases
            return resp.text
