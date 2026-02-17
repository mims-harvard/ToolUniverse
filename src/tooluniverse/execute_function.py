from .utils import read_json_list, evaluate_function_call, extract_function_call_json
import copy
import json
import random
import string
from .graphql_tool import (
    OpentargetTool,
    OpentargetGeneticsTool,
    OpentargetToolDrugNameMatch,
)
from .openfda_tool import (
    FDADrugLabelTool,
    FDADrugLabelSearchTool,
    FDADrugLabelSearchIDTool,
    FDADrugLabelGetDrugGenericNameTool,
)
from .restful_tool import MonarchTool, MonarchDiseasesForMultiplePhenoTool
from .ndex_tool import NDExTool
from .go_api_tool import GOAPITool
from .ensembl_compara_tool import EnsemblComparaTool
from .monarch_v3_tool import MonarchV3Tool
from .ebi_proteins_ext_tool import EBIProteinsExtTool
from .rcsb_data_tool import RCSBDataTool
from .ebi_proteins_features_tool import EBIProteinsFeaturesTool
from .interpro_ext_tool import InterProExtTool
from .string_ext_tool import STRINGExtTool
from .ensembl_info_tool import EnsemblInfoTool
from .three_d_beacons_tool import ThreeDBeaconsTool
from .reactome_content_tool import ReactomeContentTool
from .interpro_entry_tool import InterProEntryTool
from .ensembl_sequence_tool import EnsemblSequenceTool

import os

# Use the full default_config with all tool files
from .default_config import default_tool_files

tool_type_mappings = {
    "OpenTarget": OpentargetTool,
    "OpenTargetGenetics": OpentargetGeneticsTool,
    "FDADrugLabel": FDADrugLabelTool,
    "FDADrugLabelSearchTool": FDADrugLabelSearchTool,
    "Monarch": MonarchTool,
    "MonarchDiseasesForMultiplePheno": MonarchDiseasesForMultiplePhenoTool,
    "FDADrugLabelSearchIDTool": FDADrugLabelSearchIDTool,
    "FDADrugLabelGetDrugGenericNameTool": FDADrugLabelGetDrugGenericNameTool,
    "OpentargetToolDrugNameMatch": OpentargetToolDrugNameMatch,
    "NDExTool": NDExTool,
    "GOAPITool": GOAPITool,
    "EnsemblComparaTool": EnsemblComparaTool,
    "MonarchV3Tool": MonarchV3Tool,
    "EBIProteinsExtTool": EBIProteinsExtTool,
    "RCSBDataTool": RCSBDataTool,
    "EBIProteinsFeaturesTool": EBIProteinsFeaturesTool,
    "InterProExtTool": InterProExtTool,
    "STRINGExtTool": STRINGExtTool,
    "EnsemblInfoTool": EnsemblInfoTool,
    "ThreeDBeaconsTool": ThreeDBeaconsTool,
    "ReactomeContentTool": ReactomeContentTool,
    "InterProEntryTool": InterProEntryTool,
    "EnsemblSequenceTool": EnsemblSequenceTool,
}


class ToolUniverse:
    def __init__(self, tool_files=default_tool_files, keep_default_tools=True):
        # Initialize any necessary attributes here
        self.all_tools = []
        self.all_tool_dict = {}
        self.tool_category_dicts = {}
        if tool_files is None:
            tool_files = default_tool_files
        elif keep_default_tools:
            default_tool_files.update(tool_files)
            tool_files = default_tool_files
        self.tool_files = tool_files
        print("Tool files:")
        print(tool_files)
        self.callable_functions = {}

    def load_tools(self, tool_type=None):
        print(f"Number of tools before load tools: {len(self.all_tools)}")
        if tool_type is None:
            for each in self.tool_files:
                loaded_tool_list = read_json_list(self.tool_files[each])
                self.all_tools += loaded_tool_list
                self.tool_category_dicts[each] = loaded_tool_list
        else:
            for each in tool_type:
                loaded_tool_list = read_json_list(self.tool_files[each])
                self.all_tools += loaded_tool_list
                self.tool_category_dicts[each] = loaded_tool_list
        # Deduplication of tools
        tool_name_list = []
        dedup_all_tools = []
        for each in self.all_tools:
            if each["name"] not in tool_name_list:
                tool_name_list.append(each["name"])
                dedup_all_tools.append(each)
        self.all_tools = dedup_all_tools
        self.refresh_tool_name_desc()

        print(f"Number of tools after load tools: {len(self.all_tools)}")

    def return_all_loaded_tools(self):
        return copy.deepcopy(self.all_tools)

    def refresh_tool_name_desc(self, enable_full_desc=False):
        tool_name_list = []
        tool_desc_list = []
        for tool in self.all_tools:
            tool_name_list.append(tool["name"])
            if enable_full_desc:
                tool_desc_list.append(json.dumps(tool))
            else:
                tool_desc_list.append(tool["name"] + ": " + tool["description"])
            self.all_tool_dict[tool["name"]] = tool
        return tool_name_list, tool_desc_list

    def prepare_one_tool_prompt(self, tool):
        valid_keys = ["name", "description", "parameter", "required"]
        tool = copy.deepcopy(tool)
        for key in list(tool.keys()):
            if key not in valid_keys:
                del tool[key]
        return tool

    def prepare_tool_prompts(self, tool_list):
        copied_list = []
        for tool in tool_list:
            copied_list.append(self.prepare_one_tool_prompt(tool))
        return copied_list

    def remove_keys(self, tool_list, invalid_keys):
        copied_list = copy.deepcopy(tool_list)
        for tool in copied_list:
            # Create a list of keys to avoid modifying the dictionary during iteration
            for key in list(tool.keys()):
                if key in invalid_keys:
                    del tool[key]
        return copied_list

    def prepare_tool_examples(self, tool_list):
        valid_keys = [
            "name",
            "description",
            "parameter",
            "required",
            "query_schema",
            "fields",
            "label",
            "type",
        ]
        copied_list = copy.deepcopy(tool_list)
        for tool in copied_list:
            # Create a list of keys to avoid modifying the dictionary during iteration
            for key in list(tool.keys()):
                if key not in valid_keys:
                    del tool[key]
        return copied_list

    def get_tool_by_name(self, tool_names):
        picked_tool_list = []
        for each_name in tool_names:
            if each_name in self.all_tool_dict:
                picked_tool_list.append(self.all_tool_dict[each_name])
            else:
                print(f"Tool name {each_name} not found in the loaded tools.")
        return picked_tool_list

    def get_one_tool_by_one_name(self, tool_name, return_prompt=False):
        if tool_name in self.all_tool_dict:
            if return_prompt:
                return self.prepare_one_tool_prompt(self.all_tool_dict[tool_name])
            return self.all_tool_dict[tool_name]
        else:
            print(f"Tool name {tool_name} not found in the loaded tools.")
            return None

    def get_tool_type_by_name(self, tool_name):
        return self.all_tool_dict[tool_name]["type"]

    def tool_to_str(self, tool_list):
        return "\n\n".join(json.dumps(obj, indent=4) for obj in tool_list)

    def extract_function_call_json(self, lst, return_message=False, verbose=True):
        return extract_function_call_json(
            lst, return_message=return_message, verbose=verbose
        )

    def call_id_gen(self):
        return "".join(random.choices(string.ascii_letters + string.digits, k=9))

    def run(self, fcall_str, return_message=False, verbose=True):
        if return_message:
            function_call_json, message = self.extract_function_call_json(
                fcall_str, return_message=return_message, verbose=verbose
            )
        else:
            function_call_json = self.extract_function_call_json(
                fcall_str, return_message=return_message, verbose=verbose
            )
        if function_call_json is not None:
            if isinstance(function_call_json, list):
                # return the function call+result message with call id.
                call_results = []
                for i in range(len(function_call_json)):
                    call_result = self.run_one_function(function_call_json[i])
                    call_id = self.call_id_gen()
                    function_call_json[i]["call_id"] = call_id
                    call_results.append(
                        {
                            "role": "tool",
                            "content": json.dumps(
                                {"content": call_result, "call_id": call_id}
                            ),
                        }
                    )
                revised_messages = [
                    {
                        "role": "assistant",
                        "content": message,
                        "tool_calls": json.dumps(function_call_json),
                    }
                ] + call_results
                return revised_messages
            else:
                return self.run_one_function(function_call_json)
        else:
            print("\033[91mNot a function call\033[0m")
            return None

    def run_one_function(self, function_call_json):
        check_status, check_message = self.check_function_call(function_call_json)
        if check_status is False:
            return (
                "Invalid function call: " + check_message
            )  # + "  You must correct your invalid function call!"
        function_name = function_call_json["name"]
        arguments = function_call_json["arguments"]
        if function_name in self.callable_functions:
            return self.callable_functions[function_name].run(arguments)
        else:
            if function_name in self.all_tool_dict:
                print(
                    "\033[92mInitiating callable_function from loaded tool dicts.\033[0m"
                )
                tool = self.init_tool(
                    self.all_tool_dict[function_name], add_to_cache=True
                )
                return tool.run(arguments)

    def init_tool(self, tool=None, tool_name=None, add_to_cache=True):
        if tool_name is not None:
            if tool_name in tool_type_mappings:
                new_tool = tool_type_mappings[tool_name]()
            else:
                from .tool_registry import get_tool_class_lazy

                tool_class = get_tool_class_lazy(tool_name)
                if tool_class is None:
                    raise KeyError(f"Tool type '{tool_name}' not found in registry")
                new_tool = tool_class()
        else:
            tool_type = tool["type"]
            tool_name = tool["name"]
            if "OpentargetToolDrugNameMatch" == tool_type:
                if "FDADrugLabelGetDrugGenericNameTool" not in self.callable_functions:
                    self.callable_functions["FDADrugLabelGetDrugGenericNameTool"] = (
                        tool_type_mappings["FDADrugLabelGetDrugGenericNameTool"]()
                    )
                new_tool = tool_type_mappings[tool_type](
                    tool_config=tool,
                    drug_generic_tool=self.callable_functions[
                        "FDADrugLabelGetDrugGenericNameTool"
                    ],
                )
            elif tool_type in tool_type_mappings:
                new_tool = tool_type_mappings[tool_type](tool_config=tool)
            else:
                # Fall back to the lazy tool registry for types not in tool_type_mappings
                from .tool_registry import get_tool_class_lazy

                tool_class = get_tool_class_lazy(tool_type)
                if tool_class is None:
                    raise KeyError(
                        f"Tool type '{tool_type}' not found in registry or tool_type_mappings"
                    )
                new_tool = tool_class(tool_config=tool)
        if add_to_cache:
            self.callable_functions[tool_name] = new_tool
        return new_tool

    def check_function_call(self, fcall_str, function_config=None):
        function_call_json = self.extract_function_call_json(fcall_str)
        print("loaded function call json", function_call_json)
        if function_call_json is not None:
            if function_config is not None:
                return evaluate_function_call(function_config, function_call_json)
            function_name = function_call_json["name"]
            if function_name not in self.all_tool_dict:
                return (
                    False,
                    f"Function name {function_name} not found in loaded tools.",
                )
            return evaluate_function_call(
                self.all_tool_dict[function_name], function_call_json
            )
        else:
            return False, "\033[91mInvalid JSON string of function call\033[0m"
