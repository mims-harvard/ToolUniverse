import requests
import re
from typing import Dict, Any, Optional, List
from .base_tool import BaseTool
from .tool_registry import register_tool

WHO_GHO_BASE_URL = "https://ghoapi.azureedge.net/api"

# Common country name to ISO code mappings
COUNTRY_MAPPINGS = {
    "usa": "USA",
    "united states": "USA",
    "us": "USA",
    "uk": "GBR",
    "united kingdom": "GBR",
    "britain": "GBR",
    "china": "CHN",
    "chinese": "CHN",
    "india": "IND",
    "indian": "IND",
    "japan": "JPN",
    "japanese": "JPN",
    "germany": "DEU",
    "german": "DEU",
    "france": "FRA",
    "french": "FRA",
    "italy": "ITA",
    "italian": "ITA",
    "spain": "ESP",
    "spanish": "ESP",
    "canada": "CAN",
    "canadian": "CAN",
    "australia": "AUS",
    "australian": "AUS",
    "brazil": "BRA",
    "brazilian": "BRA",
    "russia": "RUS",
    "russian": "RUS",
    "south korea": "KOR",
    "korea": "KOR",
    "mexico": "MEX",
    "mexican": "MEX",
}


@register_tool("WHOGHORESTTool")
class WHOGHORESTTool(BaseTool):
    """Base class for WHO Global Health Observatory (GHO) REST API tools."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint = tool_config["fields"]["endpoint"]
        fields = tool_config.get("fields", {})
        self.filter_by_code = fields.get("filter_by_code", False)

    def _make_request(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make request to WHO GHO API."""
        # Build OData query parameters
        odata_params = {}
        filter_parts = []

        # Check if we need to use direct indicator endpoint format
        # WHO GHO API uses /api/{IndicatorCode} instead of /api/Data
        use_direct_indicator_endpoint = False
        indicator_code = None

        if params and "indicator_code" in params:
            indicator_code = params["indicator_code"]
            # Use direct indicator endpoint if endpoint is /Data
            if self.endpoint == "/Data":
                use_direct_indicator_endpoint = True
                # URL will be /api/{IndicatorCode} instead of /api/Data
                url = f"{WHO_GHO_BASE_URL}/{indicator_code}"
            else:
                url = f"{WHO_GHO_BASE_URL}{self.endpoint}"
        else:
            url = f"{WHO_GHO_BASE_URL}{self.endpoint}"

        if params:
            # Handle OData $filter syntax for Indicator endpoint
            if (
                self.filter_by_code
                and "indicator_code" in params
                and not use_direct_indicator_endpoint
            ):
                code = params["indicator_code"]
                filter_parts.append(f"IndicatorCode eq '{code}'")

            # Handle search term filtering for Indicator endpoint
            if "search_term" in params and params["search_term"]:
                term = params["search_term"]
                filter_parts.append(f"contains(IndicatorName, '{term}')")

            # For direct indicator endpoints, don't filter by IndicatorCode
            # (it's already in the URL path), but do filter by dimensions
            if use_direct_indicator_endpoint:
                # Handle country filtering
                if "country_code" in params and params.get("country_code"):
                    code = params["country_code"]
                    filter_parts.append(f"SpatialDim eq '{code}'")

                # Handle year filtering - don't quote numbers in OData
                if "year" in params and params.get("year") is not None:
                    year = params["year"]
                    filter_parts.append(f"TimeDim eq {year}")
            elif self.endpoint == "/Data":
                # Legacy /Data endpoint logic (kept for compatibility)
                if "indicator_code" in params:
                    code = params["indicator_code"]
                    filter_parts.append(f"IndicatorCode eq '{code}'")
                if "country_code" in params and params.get("country_code"):
                    code = params["country_code"]
                    filter_parts.append(f"SpatialDim eq '{code}'")
                if params.get("year") is not None:
                    year = params["year"]
                    filter_parts.append(f"TimeDim eq {year}")

            # Handle dimension code filtering for Dimension endpoint
            if (
                self.endpoint == "/Dimension"
                and "dimension_code" in params
                and params.get("dimension_code")
            ):
                code = params["dimension_code"]
                filter_parts.append(f"Code eq '{code}'")

            # Combine filter parts
            if filter_parts:
                odata_params["$filter"] = " and ".join(filter_parts)

            # Handle pagination
            if "top" in params:
                odata_params["$top"] = min(params["top"], 1000)  # Cap at 1000
            if "skip" in params:
                odata_params["$skip"] = params["skip"]

        try:
            resp = requests.get(url, params=odata_params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return {
                "data": data,
                "metadata": {
                    "source": "WHO Global Health Observatory",
                    "endpoint": url,
                    "query": odata_params,
                },
            }
        except requests.exceptions.RequestException as e:
            return {"error": f"Request failed: {str(e)}"}
        except ValueError as e:
            return {"error": f"Failed to parse JSON: {str(e)}", "retryable": True}

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with given arguments."""
        return self._make_request(arguments)

    @staticmethod
    def parse_query(query: str) -> Dict[str, Any]:
        """
        Parse natural language query to extract health topic, country, year.

        Parameters
        ----------
        query : str
            Natural language query (e.g., "smoking rate in USA 2020")

        Returns
        -------
        dict
            Dictionary with extracted: topic, country_code, year
        """
        query_lower = query.lower()
        result = {"topic": None, "country_code": None, "year": None}

        # Extract year (4-digit number)
        year_match = re.search(r"\b(19|20)\d{2}\b", query)
        if year_match:
            result["year"] = int(year_match.group())

        # Extract country
        for country_name, iso_code in COUNTRY_MAPPINGS.items():
            if country_name in query_lower:
                result["country_code"] = iso_code
                break

        # Extract health topic (remove country and year, keep rest)
        topic_query = query_lower
        if result["year"]:
            topic_query = re.sub(r"\b(19|20)\d{2}\b", "", topic_query)
        if result["country_code"]:
            for country_name in COUNTRY_MAPPINGS.keys():
                topic_query = topic_query.replace(country_name, "")
        # Remove common words
        common_words_pattern = r"\b(in|for|of|the|a|an|rate|prevalence|percentage)\b"
        topic_query = re.sub(common_words_pattern, "", topic_query)
        topic_query = re.sub(r"\s+", " ", topic_query).strip()
        result["topic"] = topic_query if topic_query else query_lower

        return result

    @staticmethod
    def rank_indicators(
        indicators: List[Dict[str, Any]], query: str
    ) -> List[Dict[str, Any]]:
        """
        Rank indicators by relevance to query.

        Parameters
        ----------
        indicators : list
            List of indicator dictionaries
        query : str
            Search query

        Returns
        -------
        list
            Ranked list of indicators
        """
        query_lower = query.lower()
        query_words = set(re.findall(r"\b\w+\b", query_lower))

        def score_indicator(indicator: Dict[str, Any]) -> float:
            name = indicator.get("IndicatorName", "").lower()
            code = indicator.get("IndicatorCode", "").lower()

            score = 0.0
            name_words = set(re.findall(r"\b\w+\b", name))

            # Exact phrase match
            if query_lower in name:
                score += 10.0

            # Word overlap
            common_words = query_words.intersection(name_words)
            score += len(common_words) * 2.0

            # Code relevance (if query matches code pattern)
            if any(word in code for word in query_words):
                score += 1.0

            return score

        ranked = sorted(indicators, key=score_indicator, reverse=True)
        return ranked

    @staticmethod
    def format_health_answer(
        value: Any,
        indicator_name: str,
        country_code: Optional[str] = None,
        year: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Format health data into a human-readable answer.

        Parameters
        ----------
        value : Any
            Health statistic value
        indicator_name : str
            Name of the indicator
        country_code : str, optional
            Country code
        year : int, optional
            Year

        Returns
        -------
        dict
            Formatted answer dictionary
        """
        answer_parts = []

        if value is not None:
            if isinstance(value, (int, float)):
                name_lower = indicator_name.lower()
                is_percentage = "%" in name_lower or "prevalence" in name_lower
                if is_percentage:
                    answer_parts.append(f"{value}%")
                else:
                    answer_parts.append(str(value))
            else:
                answer_parts.append(str(value))
        else:
            answer_parts.append("No data available")

        context = {
            "indicator": indicator_name,
        }

        if country_code:
            context["country"] = country_code
        if year:
            context["year"] = str(year)

        answer_text = " ".join(answer_parts) if answer_parts else "No data available"
        return {
            "answer": answer_text,
            "value": value,
            **context,
            "source": "WHO Global Health Observatory",
        }

    @staticmethod
    def is_value_available(value_obj: Dict[str, Any]) -> bool:
        """
        Check if a WHO data value is available.

        Returns False when the API returns placeholders such as
        "Data not available" or when the numeric value is missing.
        """
        if not value_obj:
            return False

        numeric = value_obj.get("NumericValue")
        text_value = value_obj.get("Value")

        if text_value == "Data not available":
            return False
        if numeric is None:
            return False

        return True

    def _make_request_for_data(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make request to data using direct indicator endpoint format."""
        if "indicator_code" not in params:
            return {"error": "indicator_code parameter is required"}

        # Use direct indicator endpoint: /api/{IndicatorCode}
        indicator_code = params["indicator_code"]
        url = f"{WHO_GHO_BASE_URL}/{indicator_code}"

        odata_params = {}
        filter_parts = []

        # Filter by country (SpatialDim)
        if "country_code" in params and params.get("country_code"):
            filter_parts.append(f"SpatialDim eq '{params['country_code']}'")

        # Filter by year (TimeDim) - don't quote numbers in OData
        if "year" in params and params.get("year"):
            year_val = params["year"]
            filter_parts.append(f"TimeDim eq {year_val}")

        if filter_parts:
            odata_params["$filter"] = " and ".join(filter_parts)
        if "top" in params:
            odata_params["$top"] = params["top"]

        try:
            resp = requests.get(url, params=odata_params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return {"data": data}
        except requests.exceptions.RequestException as e:
            return {"error": f"Request failed: {str(e)}"}
        except ValueError as e:
            return {"error": f"Failed to parse JSON: {str(e)}", "retryable": True}


@register_tool("WHOGHOQueryTool")
class WHOGHOQueryTool(WHOGHORESTTool):
    """Tool for answering generic health questions using natural language."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        # Override endpoint for query tool
        self.endpoint = "/Indicator"

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute query tool with natural language processing."""
        query = arguments.get("query", "")
        if not query:
            return {"error": "Query parameter is required"}

        # Parse query to extract topic, country, year
        parsed = self.parse_query(query)

        # Use provided country/year or extracted ones
        country_code = arguments.get("country_code") or parsed.get("country_code")
        year = arguments.get("year") or parsed.get("year")
        topic = parsed.get("topic") or query
        top = arguments.get("top", 5)

        # Step 1: Search for relevant indicators
        search_result = self._make_request(
            {
                "search_term": topic,
                "top": min(top * 3, 50),  # Get more candidates for ranking
            }
        )

        if "error" in search_result:
            return search_result

        indicators_data = search_result.get("data", {})
        indicators = indicators_data.get("value", [])

        if not indicators:
            return {
                "error": f"No indicators found for query: '{query}'",
                "suggestion": "Try different keywords or check spelling",
            }

        # Step 2: Rank indicators by relevance
        ranked_indicators = self.rank_indicators(indicators, topic)

        # Step 3: Try to get data for top indicators
        results = []
        for indicator in ranked_indicators[:top]:
            indicator_code = indicator.get("IndicatorCode")
            indicator_name = indicator.get("IndicatorName")

            # Get data for this indicator
            data_params = {"indicator_code": indicator_code, "top": 1}
            if country_code:
                data_params["country_code"] = country_code
            if year:
                data_params["year"] = year

            data_result = self._make_request_for_data(data_params)

            if "error" not in data_result:
                data_obj = data_result.get("data", {})
                values = data_obj.get("value", [])
                values = [v for v in values if self.is_value_available(v)]
                if values:
                    value_obj = values[0]
                    value = value_obj.get("NumericValue") or value_obj.get("Value")
                    result_year = value_obj.get("TimeDim") or (
                        str(year) if year else None
                    )
                    result_country = value_obj.get("SpatialDim") or country_code

                    # Convert year to int if possible
                    year_int = None
                    if result_year:
                        if isinstance(result_year, int):
                            year_int = result_year
                        elif isinstance(result_year, str) and result_year.isdigit():
                            year_int = int(result_year)
                        elif isinstance(result_year, str):
                            # Try to extract year from string
                            try:
                                year_int = int(result_year)
                            except (ValueError, TypeError):
                                year_int = None

                    formatted = self.format_health_answer(
                        value=value,
                        indicator_name=indicator_name,
                        country_code=result_country,
                        year=year_int,
                    )
                    formatted["indicator_code"] = indicator_code
                    results.append(formatted)

        if not results:
            return {
                "error": f"No data found for query: '{query}'",
                "matched_indicators": [
                    {"code": ind.get("IndicatorCode"), "name": ind.get("IndicatorName")}
                    for ind in ranked_indicators[:3]
                ],
                "suggestion": (
                    "Try a different country, year, or check if data is available"
                ),
            }

        # Return best match (first result)
        return {
            "data": results[0] if len(results) == 1 else results,
            "metadata": {
                "source": "WHO Global Health Observatory",
                "query": query,
                "indicators_searched": len(ranked_indicators),
                "results_found": len(results),
            },
        }


@register_tool("WHOGHOTopicTool")
class WHOGHOTopicTool(WHOGHORESTTool):
    """Tool for finding indicators by topic."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint = "/Indicator"

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Find indicators by topic."""
        topic = arguments.get("topic", "")
        if not topic:
            return {"error": "Topic parameter is required"}

        top = arguments.get("top", 10)

        # Search for indicators
        search_result = self._make_request(
            {
                "search_term": topic,
                "top": min(top * 2, 100),  # Get more for ranking
            }
        )

        if "error" in search_result:
            return search_result

        indicators_data = search_result.get("data", {})
        indicators = indicators_data.get("value", [])

        if not indicators:
            return {
                "error": f"No indicators found for topic: '{topic}'",
                "suggestion": "Try different keywords or check spelling",
            }

        # Rank indicators by relevance
        ranked_indicators = self.rank_indicators(indicators, topic)

        # Calculate relevance scores (simplified)
        result_indicators = []
        for idx, indicator in enumerate(ranked_indicators[:top]):
            # Simple relevance score based on position
            score = (len(ranked_indicators) - idx) / len(ranked_indicators) * 10
            result_indicators.append(
                {
                    "IndicatorCode": indicator.get("IndicatorCode"),
                    "IndicatorName": indicator.get("IndicatorName"),
                    "relevance_score": round(score, 2),
                }
            )

        return {
            "data": {
                "indicators": result_indicators,
                "topic": topic,
                "total_found": len(indicators),
            },
            "metadata": {"source": "WHO Global Health Observatory", "topic": topic},
        }


@register_tool("WHOGHOStatisticTool")
class WHOGHOStatisticTool(WHOGHORESTTool):
    """Tool for getting health statistics by indicator name."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint = "/Indicator"

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get health statistic by indicator name."""
        indicator_name = arguments.get("indicator_name", "")
        country_code = arguments.get("country_code", "")
        year = arguments.get("year")

        if not indicator_name:
            return {"error": "indicator_name parameter is required"}
        if not country_code:
            return {"error": "country_code parameter is required"}

        # Step 1: Search for matching indicator
        search_result = self._make_request({"search_term": indicator_name, "top": 20})

        if "error" in search_result:
            return search_result

        indicators_data = search_result.get("data", {})
        indicators = indicators_data.get("value", [])

        if not indicators:
            return {
                "error": f"No indicators found matching: '{indicator_name}'",
                "suggestion": "Try different keywords or check spelling",
            }

        # Step 2: Rank and get best match
        ranked_indicators = self.rank_indicators(indicators, indicator_name)
        best_indicator = ranked_indicators[0]
        indicator_code = best_indicator.get("IndicatorCode")
        full_indicator_name = best_indicator.get("IndicatorName")

        # Step 3: Get data
        data_params = {
            "indicator_code": indicator_code,
            "country_code": country_code,
            "top": 1,
        }
        if year:
            data_params["year"] = year

        data_result = self._make_request_for_data(data_params)

        if "error" in data_result:
            return {
                "error": data_result["error"],
                "indicator_found": {
                    "code": indicator_code,
                    "name": full_indicator_name,
                },
                "suggestion": (
                    "Data may not be available for this country/year combination"
                ),
            }

        data_obj = data_result.get("data", {})
        values = data_obj.get("value", [])
        values = [v for v in values if self.is_value_available(v)]

        if not values:
            # Try without year filter to get most recent
            if year:
                data_params_no_year = {
                    "indicator_code": indicator_code,
                    "country_code": country_code,
                    "top": 10,
                }
                data_result_no_year = self._make_request_for_data(data_params_no_year)
                if "error" not in data_result_no_year:
                    data_obj_no_year = data_result_no_year.get("data", {})
                    values = data_obj_no_year.get("value", [])
                    values = [v for v in values if self.is_value_available(v)]
                    if values:
                        # Get most recent year
                        values.sort(key=lambda x: x.get("TimeDim", ""), reverse=True)
                        values = [values[0]]

        if not values:
            return {
                "error": (
                    f"No data available for '{indicator_name}' in {country_code}"
                ),
                "indicator_found": {
                    "code": indicator_code,
                    "name": full_indicator_name,
                },
                "suggestion": ("Try a different country or check data availability"),
            }

        value_obj = values[0]
        value = value_obj.get("NumericValue") or value_obj.get("Value")
        result_year = value_obj.get("TimeDim") or (str(year) if year else None)
        result_country = value_obj.get("SpatialDim") or country_code

        # Convert year to int if possible
        year_int = None
        if result_year:
            if isinstance(result_year, int):
                year_int = result_year
            elif isinstance(result_year, str) and result_year.isdigit():
                year_int = int(result_year)
            elif isinstance(result_year, str):
                # Try to extract year from string
                try:
                    year_int = int(result_year)
                except (ValueError, TypeError):
                    year_int = None

        formatted = self.format_health_answer(
            value=value,
            indicator_name=full_indicator_name,
            country_code=result_country,
            year=year_int,
        )

        return {
            "data": formatted,
            "metadata": {
                "source": "WHO Global Health Observatory",
                "indicator_code": indicator_code,
            },
        }
