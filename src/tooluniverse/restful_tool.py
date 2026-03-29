from .graphql_tool import GraphQLTool, remove_none_and_empty_values
import requests
import copy
from .tool_registry import register_tool


def execute_RESTful_query(endpoint_url, variables=None):
    response = requests.get(endpoint_url, params=variables)
    try:
        result = response.json()

        if "error" in result:
            print("Invalid Query: ", result["error"])
            return False
        return result
    except requests.exceptions.JSONDecodeError:
        print("JSONDecodeError: Could not decode the response as JSON")
        return False
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error occurred: {e}")
        return False
    except Exception as e:
        print(f"An error occurred: {e}")
        return False


@register_tool("RESTfulTool")
class RESTfulTool(GraphQLTool):
    def __init__(self, tool_config, endpoint_url):
        super().__init__(tool_config, endpoint_url)

    def run(self, arguments):
        arguments = copy.deepcopy(arguments)
        return execute_RESTful_query(
            endpoint_url=self.endpoint_url, variables=arguments
        )


@register_tool("Monarch")
class MonarchTool(RESTfulTool):
    def __init__(self, tool_config):
        endpoint_url = (
            "https://api.monarchinitiative.org/v3/api" + tool_config["tool_url"]
        )
        super().__init__(tool_config, endpoint_url)

    def run(self, arguments):
        arguments = copy.deepcopy(arguments)
        query_schema_runtime = copy.deepcopy(self.query_schema)
        for key in query_schema_runtime:
            if key in arguments:
                query_schema_runtime[key] = arguments[key]
        if "url_key" in query_schema_runtime:
            url_key_name = query_schema_runtime["url_key"]
            formatted_endpoint_url = self.endpoint_url.format(
                url_key=query_schema_runtime[url_key_name]
            )
            del query_schema_runtime["url_key"]
        else:
            formatted_endpoint_url = self.endpoint_url
        if isinstance(query_schema_runtime, dict):
            if "query" in query_schema_runtime:
                query_schema_runtime["q"] = query_schema_runtime[
                    "query"
                ]  # match with the api
        response = execute_RESTful_query(
            endpoint_url=formatted_endpoint_url, variables=query_schema_runtime
        )
        if "facet_fields" in response:
            del response["facet_fields"]

        response = remove_none_and_empty_values(response)
        if isinstance(response, dict) and "status" not in response:
            return {"status": "success", "data": response}
        return response


@register_tool("MonarchDiseasesForMultiplePheno")
class MonarchDiseasesForMultiplePhenoTool(MonarchTool):
    def __init__(self, tool_config):
        super().__init__(tool_config)

    def run(self, arguments):
        arguments = copy.deepcopy(arguments)
        query_schema_runtime = copy.deepcopy(self.query_schema)
        for key in query_schema_runtime:
            if (key != "HPO_ID_list") and (key in arguments):
                query_schema_runtime[key] = arguments[key]
        all_diseases = []
        for HPOID in arguments["HPO_ID_list"]:
            each_query_schema_runtime = copy.deepcopy(query_schema_runtime)
            each_query_schema_runtime["object"] = HPOID
            each_query_schema_runtime["limit"] = 500
            each_output = execute_RESTful_query(
                endpoint_url=self.endpoint_url, variables=each_query_schema_runtime
            )
            each_output = each_output["items"]
            each_output_names = [disease["subject_label"] for disease in each_output]
            all_diseases.append(each_output_names)

        intersection = set(all_diseases[0])
        for element in all_diseases[1:]:
            intersection &= set(element)
        intersection = list(intersection)
        if query_schema_runtime["limit"] < len(intersection):
            intersection = intersection[: query_schema_runtime["limit"]]
        return intersection
