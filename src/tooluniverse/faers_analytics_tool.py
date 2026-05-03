# faers_analytics_tool.py

import requests
import math
from typing import Dict, Any, List, Tuple
from .base_tool import BaseTool
from .tool_registry import register_tool

FDA_BASE_URL = "https://api.fda.gov/drug/event.json"


@register_tool("FAERSAnalyticsTool")
class FAERSAnalyticsTool(BaseTool):
    """
    FAERS Analytics Tool for statistical signal detection in adverse event data.

    Provides:
    - Disproportionality analysis (ROR, PRR, IC, EBGM)
    - Demographic stratification
    - Serious event filtering
    - Drug comparison
    - Temporal trend analysis
    - MedDRA hierarchy rollups
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to analytics operation."""
        # Normalize aliases
        if not arguments.get("adverse_event") and arguments.get("reaction"):
            arguments = dict(arguments, adverse_event=arguments["reaction"])
        if not arguments.get("stratify_by") and arguments.get("demographic"):
            arguments = dict(arguments, stratify_by=arguments["demographic"])
        # Normalize drug_name aliases: 'drug' → 'drug_name'
        if not arguments.get("drug_name") and arguments.get("drug"):
            arguments = dict(arguments, drug_name=arguments["drug"])
        # Normalize seriousness_type alias: 'event_type' → 'seriousness_type'
        if not arguments.get("seriousness_type") and arguments.get("event_type"):
            arguments = dict(arguments, seriousness_type=arguments["event_type"])
        # Normalize compare_drugs alias: 'drugs' list → 'drug1', 'drug2'
        if arguments.get("drugs") and not arguments.get("drug1"):
            drugs_list = arguments["drugs"]
            if isinstance(drugs_list, list) and len(drugs_list) >= 2:
                arguments = dict(arguments, drug1=drugs_list[0], drug2=drugs_list[1])
        # Normalize stratify_by: 'age_group' → 'age'
        if arguments.get("stratify_by") == "age_group":
            arguments = dict(arguments, stratify_by="age")
        operation = arguments.get("operation")
        # Auto-fill operation from tool config const if not provided by user
        if not operation:
            operation = self.get_schema_const_operation()

        if not operation:
            return {"status": "error", "error": "Missing required parameter: operation"}

        if operation == "calculate_disproportionality":
            operation_result = self._calculate_disproportionality(arguments)
        elif operation == "stratify_by_demographics":
            operation_result = self._stratify_by_demographics(arguments)
        elif operation == "filter_serious_events":
            operation_result = self._filter_serious_events(arguments)
        elif operation == "compare_drugs":
            operation_result = self._compare_drugs(arguments)
        elif operation == "analyze_temporal_trends":
            operation_result = self._analyze_temporal_trends(arguments)
        elif operation == "rollup_meddra_hierarchy":
            operation_result = self._rollup_meddra_hierarchy(arguments)
        else:
            return {"status": "error", "error": f"Unknown operation: {operation}"}

        return self._with_data_payload(operation_result)

    def _with_data_payload(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure successful operation responses include a standardized data wrapper."""
        if not isinstance(result, dict):
            return {"status": "success", "data": {"value": result}, "value": result}

        if result.get("status") != "success":
            return result

        if "data" in result:
            return result

        # Feature-81A-004: move non-status keys into data to avoid duplicating
        # every field at both the top level and inside data.
        data = {k: v for k, v in result.items() if k != "status"}
        return {"status": "success", "data": data}

    def _calculate_disproportionality(
        self, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate disproportionality measures (ROR, PRR, IC) with 95% confidence intervals.

        Uses 2x2 contingency table:
                    Event+    Event-
        Drug+         a         b
        Drug-         c         d
        """
        try:
            drug_name = arguments.get("drug_name")
            adverse_event = arguments.get("adverse_event")

            if not drug_name or not adverse_event:
                return {
                    "status": "error",
                    "error": "Must provide drug_name and adverse_event",
                }

            # Get counts for 2x2 table
            # a = drug + event
            a = self._get_faers_count(drug_name, adverse_event)

            # b = drug + no event (all drug reports - drug+event)
            b = self._get_faers_count(drug_name, None) - a

            # c = no drug + event (all event reports - drug+event)
            c = self._get_faers_count(None, adverse_event) - a

            # d = no drug + no event (total - a - b - c)
            total = self._get_faers_total_count()
            d = total - a - b - c

            # Check for valid counts
            if a <= 0 or b <= 0 or c <= 0 or d <= 0:
                return {
                    "status": "error",
                    "error": f"Insufficient data: a={a}, b={b}, c={c}, d={d}. Need all counts > 0 for analysis.",
                    "contingency_table": {"a": a, "b": b, "c": c, "d": d},
                }

            # Calculate ROR (Reporting Odds Ratio)
            ror = (a / b) / (c / d) if b > 0 and d > 0 else None
            ror_ci = self._calculate_ror_ci(a, b, c, d) if ror else None

            # Calculate PRR (Proportional Reporting Ratio)
            prr = (a / (a + b)) / (c / (c + d)) if (a + b) > 0 and (c + d) > 0 else None
            prr_ci = self._calculate_prr_ci(a, b, c, d) if prr else None

            # Calculate IC (Information Component)
            ic = self._calculate_ic(a, b, c, d)
            ic_ci = self._calculate_ic_ci(a, b, c, d) if ic is not None else None

            # Determine signal strength
            signal_detected = False
            signal_strength = "No signal"

            if ror and ror_ci:
                if ror_ci["lower"] > 1.0 and a >= 3:  # Standard threshold
                    signal_detected = True
                    if ror >= 4.0:
                        signal_strength = "Strong signal"
                    elif ror >= 2.0:
                        signal_strength = "Moderate signal"
                    else:
                        signal_strength = "Weak signal"

            return {
                "status": "success",
                "drug_name": drug_name,
                "adverse_event": adverse_event,
                "contingency_table": {
                    "a_drug_and_event": a,
                    "b_drug_no_event": b,
                    "c_no_drug_event": c,
                    "d_no_drug_no_event": d,
                },
                "metrics": {
                    "ROR": {
                        "value": round(ror, 3) if ror else None,
                        "ci_95_lower": round(ror_ci["lower"], 3) if ror_ci else None,
                        "ci_95_upper": round(ror_ci["upper"], 3) if ror_ci else None,
                        "interpretation": "Reporting odds ratio - measures association strength",
                    },
                    "PRR": {
                        "value": round(prr, 3) if prr else None,
                        "ci_95_lower": round(prr_ci["lower"], 3) if prr_ci else None,
                        "ci_95_upper": round(prr_ci["upper"], 3) if prr_ci else None,
                        "interpretation": "Proportional reporting ratio - probability ratio",
                    },
                    "IC": {
                        "value": round(ic, 3) if ic is not None else None,
                        "ci_95_lower": round(ic_ci["lower"], 3) if ic_ci else None,
                        "ci_95_upper": round(ic_ci["upper"], 3) if ic_ci else None,
                        "interpretation": "Information component - Bayesian measure",
                    },
                },
                "signal_detection": {
                    "signal_detected": signal_detected,
                    "signal_strength": signal_strength,
                    "criteria": "ROR lower CI > 1.0 and case count >= 3",
                },
                "note": "Disproportionality analysis indicates potential safety signal. Does NOT prove causation. Requires clinical evaluation.",
            }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Disproportionality calculation failed: {str(e)}",
            }

    def _stratify_by_demographics(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Stratify adverse event data by demographics (age, sex, country)."""
        try:
            drug_name = arguments.get("drug_name")
            adverse_event = arguments.get("adverse_event")
            stratify_by = arguments.get("stratify_by", "sex")  # sex, age, country

            if not drug_name:
                return {
                    "status": "error",
                    "error": "Must provide drug_name",
                }

            if stratify_by not in ["sex", "age", "country"]:
                return {
                    "status": "error",
                    "error": "stratify_by must be 'sex', 'age', or 'country'",
                }

            # Map stratification to FAERS fields
            field_map = {
                "sex": "patient.patientsex",
                "age": "patient.patientagegroup",
                "country": "occurcountry",
            }

            count_field = field_map[stratify_by]

            # Feature-121A-003: adverse_event is optional — filter by drug alone if omitted
            if adverse_event:
                base_query = f'patient.drug.openfda.generic_name:"{drug_name}"+AND+patient.reaction.reactionmeddrapt:"{adverse_event}"'
            else:
                base_query = f'patient.drug.openfda.generic_name:"{drug_name}"'

            url = f"{FDA_BASE_URL}?search={base_query}&count={count_field}"

            response = requests.get(url, timeout=30)
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])

            # Format stratified data
            stratified_data = []
            total_count = sum(r.get("count", 0) for r in results)

            for result in results:
                term = result.get("term", "Unknown")
                count = result.get("count", 0)
                percentage = (count / total_count * 100) if total_count > 0 else 0

                # Interpret codes (API returns integers; normalize to str for dict lookup)
                term_key = str(term)
                if stratify_by == "sex":
                    term = {"0": "Unknown", "1": "Male", "2": "Female"}.get(
                        term_key, term
                    )
                elif stratify_by == "age":
                    age_map = {
                        "1": "Neonate",
                        "2": "Infant",
                        "3": "Child",
                        "4": "Adolescent",
                        "5": "Adult",
                        "6": "Elderly",
                    }
                    term = age_map.get(term_key, term)

                stratified_data.append(
                    {"group": term, "count": count, "percentage": round(percentage, 2)}
                )

            return {
                "status": "success",
                "drug_name": drug_name,
                "adverse_event": adverse_event,
                "stratified_by": stratify_by,
                "total_reports": total_count,
                "stratification": sorted(
                    stratified_data, key=lambda x: x["count"], reverse=True
                ),
            }

        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"API request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Stratification failed: {str(e)}"}

    def _filter_serious_events(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Filter for serious adverse events (death, hospitalization, disability, life-threatening)."""
        try:
            drug_name = arguments.get("drug_name")
            adverse_event = arguments.get("adverse_event")
            seriousness_type = arguments.get(
                "seriousness_type", "all"
            )  # all, death, hospitalization, disability, life_threatening

            if not drug_name:
                return {"status": "error", "error": "Must provide drug_name"}

            # Build query for serious events
            base_query = f'patient.drug.openfda.generic_name:"{drug_name}"'

            # Add specific reaction filter if provided
            if adverse_event:
                base_query += (
                    f'+AND+patient.reaction.reactionmeddrapt:"{adverse_event}"'
                )

            # Add seriousness filter
            seriousness_map = {
                "all": "+AND+serious:1",
                "death": "+AND+seriousnessdeath:1",
                "hospitalization": "+AND+seriousnesshospitalization:1",
                "disability": "+AND+seriousnessdisabling:1",
                "life_threatening": "+AND+seriousnesslifethreatening:1",
            }

            if seriousness_type not in seriousness_map:
                return {
                    "status": "error",
                    "error": f"Invalid seriousness_type. Must be one of: {list(seriousness_map.keys())}",
                }

            search_query = base_query + seriousness_map[seriousness_type]

            # Get top reactions for serious events
            url = f"{FDA_BASE_URL}?search={search_query}&count=patient.reaction.reactionmeddrapt.exact"

            response = requests.get(url, timeout=30)
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])

            # Get total serious event count
            total_url = f"{FDA_BASE_URL}?search={search_query}&limit=1"
            total_response = requests.get(total_url, timeout=30)
            total_data = total_response.json()
            total_serious = (
                total_data.get("meta", {}).get("results", {}).get("total", 0)
            )

            # Format results
            serious_reactions = []
            for result in results[:20]:  # Top 20
                serious_reactions.append(
                    {"reaction": result.get("term"), "count": result.get("count")}
                )

            result: Dict[str, Any] = {
                "drug_name": drug_name,
                "seriousness_type": seriousness_type,
                "total_serious_events": total_serious,
                "top_serious_reactions": serious_reactions,
                "note": f"Serious events: {'All' if seriousness_type == 'all' else seriousness_type.replace('_', ' ')}",
            }
            if adverse_event:
                result["adverse_event_filter"] = adverse_event.upper()
            return {"status": "success", "data": result}

        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"API request failed: {str(e)}"}
        except Exception as e:
            return {
                "status": "error",
                "error": f"Serious event filtering failed: {str(e)}",
            }

    def _compare_drugs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Compare safety profiles of two drugs for the same adverse event."""
        try:
            drug1 = arguments.get("drug1")
            drug2 = arguments.get("drug2")
            adverse_event = arguments.get("adverse_event")

            if not drug1 or not drug2 or not adverse_event:
                return {
                    "status": "error",
                    "error": "Must provide drug1, drug2, and adverse_event",
                }

            # Calculate disproportionality for both drugs
            result1 = self._calculate_disproportionality(
                {
                    "operation": "calculate_disproportionality",
                    "drug_name": drug1,
                    "adverse_event": adverse_event,
                }
            )

            result2 = self._calculate_disproportionality(
                {
                    "operation": "calculate_disproportionality",
                    "drug_name": drug2,
                    "adverse_event": adverse_event,
                }
            )

            if result1.get("status") != "success" or result2.get("status") != "success":
                return {
                    "status": "error",
                    "error": "Failed to calculate metrics for one or both drugs",
                    "drug1_result": result1,
                    "drug2_result": result2,
                }

            # Extract ROR values
            ror1 = result1.get("metrics", {}).get("ROR", {}).get("value")
            ror2 = result2.get("metrics", {}).get("ROR", {}).get("value")

            # Determine which drug has stronger signal
            comparison = "Inconclusive"
            if ror1 and ror2:
                if ror1 > ror2 * 1.5:
                    comparison = f"{drug1} shows stronger signal than {drug2}"
                elif ror2 > ror1 * 1.5:
                    comparison = f"{drug2} shows stronger signal than {drug1}"
                else:
                    comparison = f"{drug1} and {drug2} show similar signals"

            return {
                "status": "success",
                "adverse_event": adverse_event,
                "drug1": {
                    "name": drug1,
                    "metrics": result1.get("metrics"),
                    "signal_detection": result1.get("signal_detection"),
                },
                "drug2": {
                    "name": drug2,
                    "metrics": result2.get("metrics"),
                    "signal_detection": result2.get("signal_detection"),
                },
                "comparison": comparison,
                "note": "Direct comparison of safety signals. Both drugs may show signals due to different baseline risks.",
            }

        except Exception as e:
            return {"status": "error", "error": f"Drug comparison failed: {str(e)}"}

    def _analyze_temporal_trends(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze temporal trends in adverse event reporting."""
        try:
            drug_name = arguments.get("drug_name")
            adverse_event = arguments.get("adverse_event")

            if not drug_name:
                return {"status": "error", "error": "Must provide drug_name"}

            # Build base query
            if adverse_event:
                search_query = f'patient.drug.openfda.generic_name:"{drug_name}"+AND+patient.reaction.reactionmeddrapt:"{adverse_event}"'
            else:
                search_query = f'patient.drug.openfda.generic_name:"{drug_name}"'

            # Get counts by receive date (year)
            url = f"{FDA_BASE_URL}?search={search_query}&count=receivedate"

            response = requests.get(url, timeout=30)
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])

            # Parse and aggregate by year
            yearly_counts = {}
            for result in results:
                # OpenFDA count=receivedate returns "time" key, not "term"
                date_str = result.get("time") or result.get("term", "")
                if len(date_str) >= 4:
                    year = date_str[:4]
                    count = result.get("count", 0)
                    yearly_counts[year] = yearly_counts.get(year, 0) + count

            # Format temporal data
            temporal_data = [
                {"year": year, "count": count}
                for year, count in sorted(yearly_counts.items())
            ]

            # Calculate trend
            if len(temporal_data) >= 2:
                first_year_count = temporal_data[0]["count"]
                last_year_count = temporal_data[-1]["count"]
                percent_change = (
                    ((last_year_count - first_year_count) / first_year_count * 100)
                    if first_year_count > 0
                    else 0
                )
                trend = (
                    "Increasing"
                    if percent_change > 10
                    else ("Decreasing" if percent_change < -10 else "Stable")
                )
            else:
                percent_change = 0
                trend = "Insufficient data"

            return {
                "status": "success",
                "drug_name": drug_name,
                "adverse_event": adverse_event or "All events",
                "temporal_data": temporal_data,
                "trend_analysis": {
                    "trend": trend,
                    "percent_change": round(percent_change, 1),
                    "years_analyzed": len(temporal_data),
                },
                "note": "Temporal trends may reflect increased awareness, reporting, or actual incidence changes",
            }

        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"API request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Temporal analysis failed: {str(e)}"}

    def _rollup_meddra_hierarchy(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate adverse events by MedDRA hierarchy levels (PT → HLT → SOC)."""
        try:
            drug_name = arguments.get("drug_name")

            if not drug_name:
                return {"status": "error", "error": "Must provide drug_name"}

            # Get preferred term (PT) level reactions
            search_query = f'patient.drug.openfda.generic_name:"{drug_name}"'
            url = f"{FDA_BASE_URL}?search={search_query}&count=patient.reaction.reactionmeddrapt.exact"

            response = requests.get(url, timeout=30)
            response.raise_for_status()

            data = response.json()
            pt_results = data.get("results", [])

            # Format PT level
            pt_level = [
                {"preferred_term": r.get("term"), "count": r.get("count")}
                for r in pt_results[:50]  # Top 50 PTs
            ]

            # Note: Full MedDRA hierarchy requires MedDRA license
            # FAERS API doesn't provide HLT/SOC directly

            return {
                "status": "success",
                "data": {
                    "drug_name": drug_name,
                    "meddra_hierarchy": {
                        "PT_level": pt_level,
                        "total_unique_PTs": len(pt_level),
                    },
                    "note": "Full MedDRA hierarchy (HLT, SOC) requires MedDRA license. Showing Preferred Term (PT) level only.",
                    "recommendation": "Use MedDRA dictionary to map PTs to higher-level terms for system organ class analysis",
                },
            }

        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"API request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"MedDRA rollup failed: {str(e)}"}

    # Helper methods for statistical calculations

    def _get_faers_count(self, drug_name: str = None, adverse_event: str = None) -> int:
        """Get count of FAERS reports matching criteria."""
        try:
            query_parts = []
            if drug_name:
                query_parts.append(f'patient.drug.openfda.generic_name:"{drug_name}"')
            if adverse_event:
                query_parts.append(
                    f'patient.reaction.reactionmeddrapt:"{adverse_event}"'
                )

            if not query_parts:
                # Get total count
                url = f"{FDA_BASE_URL}?limit=1"
            else:
                search_query = "+AND+".join(query_parts)
                url = f"{FDA_BASE_URL}?search={search_query}&limit=1"

            response = requests.get(url, timeout=30)
            response.raise_for_status()

            data = response.json()
            return data.get("meta", {}).get("results", {}).get("total", 0)

        except Exception:
            return 0

    def _get_faers_total_count(self) -> int:
        """Get total number of reports in FAERS database."""
        return self._get_faers_count(None, None)

    def _calculate_ror_ci(self, a: int, b: int, c: int, d: int) -> Dict[str, float]:
        """Calculate 95% confidence interval for ROR."""
        ror = (a / b) / (c / d)
        se_log_ror = math.sqrt((1 / a) + (1 / b) + (1 / c) + (1 / d))
        log_ror = math.log(ror)

        # 95% CI (z = 1.96)
        lower = math.exp(log_ror - 1.96 * se_log_ror)
        upper = math.exp(log_ror + 1.96 * se_log_ror)

        return {"lower": lower, "upper": upper}

    def _calculate_prr_ci(self, a: int, b: int, c: int, d: int) -> Dict[str, float]:
        """Calculate 95% confidence interval for PRR."""
        prr = (a / (a + b)) / (c / (c + d))
        se_log_prr = math.sqrt((b / (a * (a + b))) + (d / (c * (c + d))))
        log_prr = math.log(prr)

        lower = math.exp(log_prr - 1.96 * se_log_prr)
        upper = math.exp(log_prr + 1.96 * se_log_prr)

        return {"lower": lower, "upper": upper}

    def _calculate_ic(self, a: int, b: int, c: int, d: int) -> float:
        """Calculate Information Component (IC)."""
        n = a + b + c + d
        expected = ((a + b) * (a + c)) / n

        if expected <= 0 or a <= 0:
            return 0.0

        ic = math.log2((a + 0.5) / (expected + 0.5))
        return ic

    def _calculate_ic_ci(self, a: int, b: int, c: int, d: int) -> Dict[str, float]:
        """Calculate 95% confidence interval for IC."""
        n = a + b + c + d
        expected = ((a + b) * (a + c)) / n

        if expected <= 0 or a <= 0:
            return {"lower": 0.0, "upper": 0.0}

        # Approximate variance
        variance = (
            (1 / (a + 0.5))
            - (1 / ((a + b) + 0.5))
            - (1 / ((a + c) + 0.5))
            + (1 / (n + 0.5))
        )
        se = math.sqrt(variance) / math.log(2)

        ic = self._calculate_ic(a, b, c, d)
        lower = ic - 1.96 * se
        upper = ic + 1.96 * se

        return {"lower": lower, "upper": upper}
