from __future__ import annotations

import threading
from typing import Any, Callable, Dict, List, Optional

from .base_tool import BaseTool
from .tool_registry import register_tool

# Global lock for stdout/stderr redirection (for thread safety)
_STREAM_LOCK = threading.Lock()


def _safe_import(module_path: str, symbol: str):
    """Safely import a symbol from a module, raising a helpful error if missing."""
    try:
        module = __import__(module_path, fromlist=[symbol])
        return getattr(module, symbol)
    except Exception as e:  # noqa: BLE001
        raise ImportError(
            f"Failed to import '{symbol}' from '{module_path}'. Please install and configure 'smolagents'. Original error: {e}"
        )


class ToolUniverseTool:  # Lazy base; will subclass smolagents.Tool at runtime
    """
    Adapter that wraps a ToolUniverse tool and exposes it as a smolagents Tool.

    We create the real subclass dynamically to avoid hard dependency when the
    module is imported without smolagents installed.
    """

    def __new__(cls, *args, **kwargs):  # pragma: no cover - construct dynamic subclass
        # Import here to avoid import-time dependency when not used
        Tool = _safe_import("smolagents", "Tool")

        # Arguments: tool_name, tooluniverse_instance, tool_config
        tool_name: str = args[0]
        tooluniverse_instance = args[1]
        tool_config = args[2] if len(args) > 2 else None

        tu_config = getattr(tooluniverse_instance, "all_tool_dict", {}).get(
            tool_name, {}
        )

        # Helpers to build class attributes
        def _convert_parameter_schema(parameter_schema: Dict) -> Dict:
            properties = parameter_schema.get("properties", {})
            required = set(parameter_schema.get("required", []) or [])
            inputs: Dict[str, Dict[str, Any]] = {}
            for param_name, info in properties.items():
                entry: Dict[str, Any] = {
                    "type": info.get("type", "string"),
                    "description": info.get("description", ""),
                }
                # All optional parameters (not in required list) should be nullable
                if param_name not in required:
                    entry["nullable"] = True
                inputs[param_name] = entry
            return inputs

        def _infer_output_type(return_schema: Dict) -> str:
            schema_type = return_schema.get("type", "string")
            mapping = {
                "object": "string",
                "array": "string",
                "string": "string",
                "integer": "integer",
                "number": "number",
                "boolean": "boolean",
            }
            return mapping.get(schema_type, "string")

        inputs_schema = _convert_parameter_schema(tu_config.get("parameter", {}))
        output_type = _infer_output_type(tu_config.get("return_schema", {}))

        # Build a forward function with explicit parameters to satisfy
        # smolagents' validation (parameters must match keys in `inputs`).
        def __call_tool(
            self, __kwargs, _tool_name=tool_name, _tu=tooluniverse_instance
        ):
            try:
                result = _tu.run_one_function(
                    {"name": _tool_name, "arguments": __kwargs}
                )
                if isinstance(result, dict):
                    import json

                    return json.dumps(result, ensure_ascii=False)
                return result
            except Exception as e:  # noqa: BLE001
                return f"Error executing tool {_tool_name}: {e}"

        param_names = list(inputs_schema.keys())
        if param_names:
            # Dynamically create a function with signature: (self, p1, p2=None, ...)
            # Required params have no default, nullable params get =None
            # In Python, parameters with defaults must come after those without
            parameter_schema = tu_config.get("parameter", {})
            required = set(parameter_schema.get("required", []) or [])
            required_params = [p for p in param_names if p in required]
            optional_params = [p for p in param_names if p not in required]
            # Build signature: required params first, then optional with =None
            params_list = required_params + [f"{p}=None" for p in optional_params]
            params_sig = ", ".join(params_list)
            body_lines = ["    _kwargs = {"]
            for p in param_names:
                body_lines.append(f"        '{p}': {p},")
            body_lines.append("    }")
            body_lines.append("    return __call_tool(self, _kwargs)")
            func_src = [f"def _forward(self, {params_sig}):"] + body_lines
            func_src = "\n".join(func_src)
            ns: Dict[str, Any] = {"__call_tool": __call_tool}
            exec(func_src, ns)
            _forward = ns["_forward"]  # type: ignore[assignment]
        else:
            # No inputs -> 0-arg forward
            def _forward(self):  # type: ignore[override]
                return __call_tool(self, {})

        attrs = {
            "name": tool_name,
            "description": tu_config.get("description", ""),
            "inputs": inputs_schema,
            "output_type": output_type,
            "forward": _forward,
            "tool_config": tool_config or {},
        }

        DynamicToolCls = type(f"ToolUniverseTool_{tool_name}", (Tool,), attrs)  # type: ignore[misc]
        return DynamicToolCls()

    @classmethod
    def from_tooluniverse(
        cls,
        tool_name: str,
        tooluniverse_instance,
        tool_config: Optional[Dict[str, Any]] = None,
    ):
        """Factory to create a smolagents-compatible Tool from a ToolUniverse tool.

        This mirrors common factory patterns (e.g., from_langchain) and returns
        an instance of the dynamically constructed Tool subclass.
        """
        return cls(tool_name, tooluniverse_instance, tool_config or {})


@register_tool("SmolAgentTool")
class SmolAgentTool(BaseTool):
    """Wrap smolagents agents so they can be used as ToolUniverse tools.

    Supports:
    - CodeAgent, ToolCallingAgent, Agent, ManagedAgent
    - Mixed tools: ToolUniverse tools and smolagents-native tools
    - Streaming integration with ToolUniverse stream callbacks
    """

    def __init__(self, tool_config: Dict[str, Any], tooluniverse=None):
        super().__init__(tool_config)
        settings = tool_config.get("settings", {})

        self.agent_type: str = settings.get("agent_type", "CodeAgent")
        self.available_tools: List[Any] = settings.get("available_tools", [])
        self.model_config: Dict[str, Any] = settings.get("model", {})
        self.agent_init_params: Dict[str, Any] = settings.get("agent_init_params", {})
        self.sub_agents_config: List[Dict[str, Any]] = settings.get("sub_agents", [])

        # Set by ToolUniverse runtime or passed as parameter
        self.tooluniverse = tooluniverse
        self.agent = None

    # -------------------------
    # Initialization helpers
    # -------------------------
    def _get_api_key(self) -> Optional[str]:
        api_key = self.model_config.get("api_key")
        if isinstance(api_key, str) and api_key.startswith("env:"):
            import os

            return os.environ.get(api_key[4:])
        return api_key

    def _init_model(self):
        provider = self.model_config.get("provider", "HfApiModel")
        model_id = self.model_config.get("model_id")
        api_key = self._get_api_key()

        if provider == "HfApiModel":
            HfApiModel = _safe_import("smolagents", "HfApiModel")
            return HfApiModel(model_id, token=api_key)
        if provider == "OpenAIModel":
            OpenAIModel = _safe_import("smolagents", "OpenAIModel")
            return OpenAIModel(
                model_id=model_id,
                api_key=api_key,
                api_base=self.model_config.get("api_base"),
            )
        if provider == "LiteLLMModel":
            LiteLLMModel = _safe_import("smolagents", "LiteLLMModel")
            return LiteLLMModel(model_id=model_id, api_key=api_key)
        if provider == "InferenceClientModel":
            InferenceClientModel = _safe_import("smolagents", "InferenceClientModel")
            return InferenceClientModel(
                model_id=model_id,
                provider=self.model_config.get("provider_name"),
                token=api_key,
            )
        if provider == "TransformersModel":
            TransformersModel = _safe_import("smolagents", "TransformersModel")
            return TransformersModel(
                model_id=model_id,
            )
        if provider == "AzureOpenAIModel":
            AzureOpenAIModel = _safe_import("smolagents", "AzureOpenAIModel")
            return AzureOpenAIModel(
                model_id=model_id,
                azure_endpoint=self.model_config.get("azure_endpoint"),
                api_key=api_key,
                api_version=self.model_config.get("api_version"),
            )
        if provider == "AmazonBedrockModel":
            AmazonBedrockModel = _safe_import("smolagents", "AmazonBedrockModel")
            return AmazonBedrockModel(model_id=model_id)

        raise ValueError(f"Unsupported model provider: {provider}")

    def _import_smolagents_tool(self, class_name: str, import_path: str):
        """Dynamically import smolagents tool class with helpful error messages."""
        import importlib

        try:
            module = importlib.import_module(import_path)
        except ImportError as e:
            raise ImportError(
                f"Failed to import module '{import_path}' for smolagents tool '{class_name}'. "
                f"Please ensure the module path is correct. "
                f"Common paths include 'smolagents.tools' or 'smolagents.default_tools'. "
                f"Original error: {e}"
            ) from e

        try:
            tool_class = getattr(module, class_name)
        except AttributeError as e:
            available_attrs = [attr for attr in dir(module) if not attr.startswith("_")]
            raise AttributeError(
                f"Class '{class_name}' not found in module '{import_path}'. "
                f"Available classes in the module: {', '.join(available_attrs[:10])}"
                f"{'...' if len(available_attrs) > 10 else ''}. "
                f"Please check the class name spelling and ensure it exists in the module. "
                f"Original error: {e}"
            ) from e

        return tool_class

    def _convert_tools(self) -> List[Any]:
        """Convert mixed tool definitions to smolagents Tool instances."""
        converted: List[Any] = []
        for spec in self.available_tools:
            if isinstance(spec, str):
                converted.append(
                    ToolUniverseTool.from_tooluniverse(spec, self.tooluniverse)
                )
                continue

            if not isinstance(spec, dict):
                continue

            spec_type = spec.get("type", "tooluniverse")
            if spec_type == "smolagents":
                cls_name = spec.get("class")
                if not cls_name:
                    continue
                import_path = spec.get("import_path", "smolagents.tools")
                kwargs = spec.get("kwargs", {})
                tool_cls = self._import_smolagents_tool(cls_name, import_path)
                converted.append(tool_cls(**kwargs))
            else:
                name = spec.get("name")
                if name:
                    converted.append(
                        ToolUniverseTool.from_tooluniverse(name, self.tooluniverse)
                    )
        return converted

    def _create_sub_agents(self, sub_configs: List[Dict[str, Any]]) -> List[Any]:
        """Recursively create sub-agent instances (for ManagedAgent)."""
        sub_agents: List[Any] = []
        for cfg in sub_configs:
            sub_tool_config: Dict[str, Any] = {
                "name": cfg.get("name", "sub_agent"),
                "type": "SmolAgentTool",
                "description": cfg.get("description", ""),
                "settings": cfg,
            }
            sub_tool = SmolAgentTool(sub_tool_config, tooluniverse=self.tooluniverse)
            sub_tool._init_agent()
            if sub_tool.agent is not None:
                sub_agents.append(sub_tool.agent)
        return sub_agents

    def _init_agent(self) -> None:
        if self.agent is not None:
            return

        model = self._init_model()
        tools = self._convert_tools()

        init_kwargs: Dict[str, Any] = {"tools": tools, "model": model}
        # Give the agent an explicit name if supported
        if isinstance(self.tool_config.get("name", None), str):
            init_kwargs["name"] = self.tool_config["name"]
        init_kwargs.update(self.agent_init_params or {})

        # Sanitize unsupported kwargs based on agent type and common params
        def _sanitize(agent_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
            common_allowed = {
                "tools",
                "model",
                "name",
                "prompt_templates",
                "planning_interval",
                "stream_outputs",
                "max_steps",
            }
            codeagent_allowed = common_allowed.union(
                {
                    "add_base_tools",
                    "additional_authorized_imports",
                    "verbosity_level",
                    "executor_type",
                    "executor_kwargs",
                }
            )
            toolcalling_allowed = common_allowed
            agent_allowed = common_allowed

            if agent_type == "CodeAgent":
                allowed = codeagent_allowed
            elif agent_type == "ToolCallingAgent":
                allowed = toolcalling_allowed
            elif agent_type == "Agent" or agent_type == "ManagedAgent":
                allowed = agent_allowed
            else:
                allowed = common_allowed

            # Drop unsupported keys (e.g., max_tool_threads)
            return {k: v for k, v in params.items() if k in allowed}

        init_kwargs = _sanitize(self.agent_type, init_kwargs)

        # Construct agent by type
        if self.agent_type == "ManagedAgent":
            # Emulate a managed multi-agent system by wrapping sub-agents
            # as smolagents Tools and composing a top-level CodeAgent.
            CodeAgent = _safe_import("smolagents", "CodeAgent")

            # Convert top-level available tools
            top_tools = tools[:]

            # Build sub-agents and wrap as tools
            sub_agents = self._create_sub_agents(self.sub_agents_config)

            # Dynamically create a Tool wrapper around a smolagents agent
            Tool = _safe_import("smolagents", "Tool")

            def _wrap_agent_as_tool(agent_obj, tool_name: str):
                # smolagents expects class attributes on Tool subclasses
                def _forward(self, task: str):  # type: ignore[override]
                    return agent_obj.run(task)

                attrs = {
                    "name": tool_name,
                    "description": f"Agent tool wrapper for {tool_name}",
                    "inputs": {
                        "task": {
                            "type": "string",
                            "description": "Task for sub-agent",
                        }
                    },
                    "output_type": "string",
                    "forward": _forward,
                }
                AgentToolCls = type(f"AgentTool_{tool_name}", (Tool,), attrs)  # type: ignore[misc]
                return AgentToolCls()

            for idx, sub in enumerate(sub_agents):
                name = getattr(sub, "name", f"sub_agent_{idx + 1}")
                top_tools.append(_wrap_agent_as_tool(sub, name))

            # Construct the orchestrator agent (CodeAgent) with both native tools and agent-tools
            orchestrator_kwargs = {"tools": top_tools, "model": model}
            if isinstance(self.tool_config.get("name", None), str):
                orchestrator_kwargs["name"] = self.tool_config["name"]
            orchestrator_kwargs.update(self.agent_init_params or {})
            orchestrator_kwargs = _sanitize("CodeAgent", orchestrator_kwargs)
            self.agent = CodeAgent(**orchestrator_kwargs)
            return

        if self.agent_type == "CodeAgent":
            CodeAgent = _safe_import("smolagents", "CodeAgent")
            self.agent = CodeAgent(**init_kwargs)
            return

        if self.agent_type == "ToolCallingAgent":
            ToolCallingAgent = _safe_import("smolagents", "ToolCallingAgent")
            self.agent = ToolCallingAgent(**init_kwargs)
            return

        if self.agent_type == "Agent":
            Agent = _safe_import("smolagents", "Agent")
            self.agent = Agent(**init_kwargs)
            return

        raise ValueError(f"Unsupported agent type: {self.agent_type}")

    # -------------------------
    # Execution
    # -------------------------
    def run(
        self,
        arguments: Dict[str, Any],
        stream_callback: Optional[Callable[[str], None]] = None,
        **_: Any,
    ) -> Dict[str, Any]:
        """Execute the agent with optional streaming back into ToolUniverse.

        Supports:
        - Streaming output (when stream_callback is provided and agent.stream_outputs=True)
        - Execution timeout (via agent_init_params.max_execution_time)
        - Thread-safe stdout/stderr redirection
        """
        import sys
        import time

        self._init_agent()
        task = arguments.get("task", "")
        if not task:
            # Fallback to 'query' for agents whose parameter is named 'query'
            task = arguments.get("query", "")

        # Get max_execution_time from config (default: None = unlimited)
        max_execution_time = self.agent_init_params.get("max_execution_time")
        timeout_error: Optional[Exception] = None
        execution_completed = threading.Event()

        def _execute_with_timeout():
            """Inner function to execute agent.run with timeout protection."""
            try:
                # If streaming desired and agent supports streaming via stdout, capture and forward
                wants_stream = bool(stream_callback) and bool(
                    getattr(self.agent, "stream_outputs", False)
                )
                if wants_stream:

                    class _StreamProxy:
                        def __init__(self, cb):
                            self._cb = cb
                            self._buf = ""
                            self._last_line = None

                        def write(self, s: str):
                            if not s:
                                return
                            self._buf += s
                            while "\n" in self._buf:
                                line, self._buf = self._buf.split("\n", 1)
                                if not line.strip():
                                    continue
                                # Deduplicate consecutive identical lines
                                if line == self._last_line:
                                    continue
                                self._last_line = line
                                self._cb(line + "\n")

                        def flush(self):
                            if self._buf.strip():
                                if self._buf != self._last_line:
                                    self._cb(self._buf)
                                    self._last_line = self._buf
                                self._buf = ""

                    # Use lock to protect stdout redirection (thread-safe)
                    with _STREAM_LOCK:
                        old_stdout, old_stderr = sys.stdout, sys.stderr
                        proxy = _StreamProxy(stream_callback)
                        sys.stdout = proxy  # forward stdout only to avoid dupes
                        try:
                            result = self.agent.run(task)
                        finally:
                            sys.stdout = old_stdout
                            sys.stderr = old_stderr

                    execution_completed.set()
                    return result

                # Non-streaming path (also protect with lock for consistency)
                with _STREAM_LOCK:
                    result = self.agent.run(task)
                execution_completed.set()
                return result

            except Exception as e:  # noqa: BLE001
                execution_completed.set()
                raise e

        try:
            start_time = time.time()

            # Execute with timeout if specified
            if max_execution_time is not None and max_execution_time > 0:
                import threading as th

                result_container: List[Any] = []
                exception_container: List[Exception] = []

                def _worker():
                    try:
                        result_container.append(_execute_with_timeout())
                    except Exception as e:  # noqa: BLE001
                        exception_container.append(e)

                worker_thread = th.Thread(target=_worker, daemon=True)
                worker_thread.start()
                worker_thread.join(timeout=max_execution_time)

                if worker_thread.is_alive():
                    # Timeout occurred
                    timeout_error = TimeoutError(
                        f"Agent execution exceeded maximum time limit of {max_execution_time} seconds. "
                        f"Task: {task[:100]}..."
                    )
                    if stream_callback:
                        stream_callback(f"\n[TIMEOUT] {timeout_error}\n")
                    return {
                        "output": None,
                        "success": False,
                        "error": str(timeout_error),
                        "error_type": "timeout",
                    }

                if exception_container:
                    raise exception_container[0]

                result = result_container[0] if result_container else None
            else:
                # No timeout - direct execution
                result = _execute_with_timeout()

            elapsed_time = time.time() - start_time
            return {
                "output": result,
                "success": True,
                "execution_time": elapsed_time,
            }

        except Exception as e:  # noqa: BLE001
            if stream_callback:
                stream_callback(f"\n[ERROR] {e}\n")
            return {
                "output": None,
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
            }
