"""USGS real-time water data (streamflow, gage height, water temperature).

These tools used the legacy WaterServices instantaneous-values endpoint
(waterservices.usgs.gov/nwis/iv/), which USGS is decommissioning: queries are
slowed from 2026-11-16, intentional outages start 2027-01-27 and it is shut
down on 2027-02-22 (#787). They now read the "continuous" collection of the
USGS Water Data OGC API (api.waterdata.usgs.gov/ogcapi/v1), the replacement
USGS names.

Behaviour of the new API that matters here (checked live 2026-10-10):

* Sites are ``USGS-<number>``; a bare number is prefixed here.
* ``time`` takes the same ISO 8601 durations the old ``period`` did (PT2H, P1D).
* A page is 10 values unless ``limit`` is set; ``sortby=-time`` gives the
  newest first, so the newest ``max_values`` are kept and returned in time
  order.
* An unknown site is an empty result, not an error.
* A site can have several sensors for one parameter (67 sites had more
  than one active water-temperature series, e.g. LOWER/MIDDLE/UPPER probes).
  Values are grouped by ``time_series_id`` and each series is labelled with
  its sensor (``sublocation_identifier``) from time-series-metadata, so
  readings from different sensors are never interleaved.
* Values are strings; they are returned as numbers.
* Anonymous use works. An api.data.gov key (``X-Api-Key``) raises the rate
  limit.
"""

import re
from typing import Any, Dict, List

import requests

from .base_tool import BaseTool
from .http_utils import upstream_reason_suffix
from .tool_registry import register_tool

OGC_API_URL = "https://api.waterdata.usgs.gov/ogcapi/v1/collections"
MAX_SITES = 25
DEFAULT_MAX_VALUES = 500
MAX_VALUES = 10000
_DURATION = re.compile(
    r"^P(?!$)(\d+Y)?(\d+M)?(\d+W)?(\d+D)?(T(?=\d)(\d+H)?(\d+M)?(\d+S)?)?$"
)
_SITE = re.compile(r"^(?:USGS-)?(\d{8,15})$", re.IGNORECASE)


def _number(value: Any) -> Any:
    try:
        return float(value)
    except (TypeError, ValueError):
        return value


@register_tool("USGSWaterTool")
class USGSWaterTool(BaseTool):
    """Recent continuous values for one USGS parameter at one or more sites."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        fields = tool_config.get("fields", {})
        self.parameter_code = fields.get("parameter_code", "00060")
        self.parameter_name = fields.get("parameter_name", self.parameter_code)
        self.timeout = tool_config.get("timeout", 60)

    @property
    def api_key(self) -> str:
        return self.credential("USGS_WATER_API_KEY") or ""

    def _get(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        headers = {"X-Api-Key": self.api_key} if self.api_key else {}
        response = requests.get(
            f"{OGC_API_URL}/{path}",
            params={"f": "json", **params},
            headers=headers,
            timeout=self.timeout,
        )
        if response.status_code != 200:
            raise _UpstreamError(
                f"USGS Water Data API returned HTTP {response.status_code}"
                f"{upstream_reason_suffix(response)}",
                retryable=response.status_code in (429, 500, 502, 503, 504),
            )
        return response.json()

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        raw_sites = arguments.get("sites")
        if isinstance(raw_sites, str):
            raw_sites = [s for s in re.split(r"[,\s]+", raw_sites) if s]
        sites: List[str] = []
        for site in raw_sites or []:
            match = _SITE.match(str(site).strip())
            if not match:
                return {
                    "status": "error",
                    "error": f"'{site}' is not a USGS site number (8-15 digits, "
                    "e.g. '01646500'; a 'USGS-' prefix is accepted).",
                }
            site_id = f"USGS-{match.group(1)}"
            if site_id not in sites:
                sites.append(site_id)
        if not sites:
            return {"status": "error", "error": "sites is required, e.g. '01646500'."}
        if len(sites) > MAX_SITES:
            return {
                "status": "error",
                "error": f"At most {MAX_SITES} sites per call ({len(sites)} given).",
            }

        period = (arguments.get("period") or "P1D").strip().upper()
        if not _DURATION.match(period):
            return {
                "status": "error",
                "error": f"period '{period}' is not an ISO 8601 duration "
                "(e.g. 'PT2H', 'P1D', 'P7D').",
            }
        max_values = arguments.get("max_values")
        if isinstance(max_values, bool) or not isinstance(max_values, int):
            max_values = DEFAULT_MAX_VALUES
        max_values = max(1, min(max_values, MAX_VALUES))

        try:
            locations = self._get(
                "monitoring-locations/items",
                {
                    "id": ",".join(sites),
                    "properties": "monitoring_location_name,state_name,site_type",
                    "limit": len(sites),
                },
            ).get("features", [])
            series = []
            for site_id in sites:
                page = self._get(
                    "continuous/items",
                    {
                        "monitoring_location_id": site_id,
                        "parameter_code": self.parameter_code,
                        "time": period,
                        "sortby": "-time",
                        "limit": max_values,
                        "properties": "time_series_id,time,value,unit_of_measure,"
                        "approval_status,qualifier",
                    },
                )
                features = page.get("features", [])
                if not features:
                    continue
                more = any(link.get("rel") == "next" for link in page.get("links", []))
                groups: Dict[str, List[Dict[str, Any]]] = {}
                for feature in reversed(features):
                    props = feature.get("properties") or {}
                    groups.setdefault(props.get("time_series_id") or "", []).append(
                        props
                    )
                for series_id, rows in groups.items():
                    values = [
                        {
                            "time": row.get("time"),
                            "value": _number(row.get("value")),
                            "approval_status": row.get("approval_status"),
                            "qualifier": row.get("qualifier"),
                        }
                        for row in rows
                    ]
                    series.append(
                        {
                            "site_id": site_id,
                            "time_series_id": series_id or None,
                            "sensor": None,
                            "unit": rows[0].get("unit_of_measure"),
                            "value_count": len(values),
                            "truncated": more,
                            "latest": values[-1],
                            "values": values,
                        }
                    )
            series_ids = [e["time_series_id"] for e in series if e["time_series_id"]]
            sensors = {}
            if len(series_ids) > len({e["site_id"] for e in series}):
                # Only label sensors when some site has more than one series.
                sensors = {
                    f.get("id"): (f.get("properties") or {}).get(
                        "sublocation_identifier"
                    )
                    for f in self._get(
                        "time-series-metadata/items",
                        {
                            "id": ",".join(series_ids),
                            "properties": "sublocation_identifier",
                            "limit": len(series_ids),
                        },
                    ).get("features", [])
                }
            for entry in series:
                entry["sensor"] = sensors.get(entry["time_series_id"])
        except _UpstreamError as e:
            result = {"status": "error", "error": str(e)}
            if e.retryable:
                result["retryable"] = True
            return result
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"USGS Water Data API did not answer within {self.timeout}s.",
                "retryable": True,
            }
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": f"USGS Water Data API request failed: {e}",
                "retryable": True,
            }
        except ValueError:
            return {
                "status": "error",
                "error": "USGS Water Data API returned a non-JSON response.",
                "retryable": True,
            }

        info = {f.get("id"): f for f in locations}
        for entry in series:
            location = info.get(entry["site_id"]) or {}
            props = location.get("properties") or {}
            coords = (location.get("geometry") or {}).get("coordinates") or [None, None]
            entry.update(
                site_number=entry["site_id"].split("-", 1)[1],
                site_name=props.get("monitoring_location_name"),
                state=props.get("state_name"),
                site_type=props.get("site_type"),
                longitude=coords[0],
                latitude=coords[1],
            )
        missing = [s for s in sites if s not in {e["site_id"] for e in series}]
        metadata = {
            "source": "USGS Water Data API (continuous values)",
            "parameter_code": self.parameter_code,
            "parameter": self.parameter_name,
            "period": period,
            "sites_requested": len(sites),
            "sites_with_data": len(series),
        }
        if missing:
            metadata["sites_without_data"] = [s.split("-", 1)[1] for s in missing]
            metadata["note"] = (
                f"No {self.parameter_name} values in the last {period} for "
                f"{', '.join(metadata['sites_without_data'])}: the site may not "
                "measure this parameter, may report with a delay, or may not exist."
            )
        if any(e["truncated"] for e in series):
            metadata["truncation_note"] = (
                f"Some series had more than {max_values} values in {period}; the "
                "newest are returned. Raise max_values (up to 10000) or shorten "
                "period."
            )
        return {"status": "success", "data": series, "metadata": metadata}


class _UpstreamError(Exception):
    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable
