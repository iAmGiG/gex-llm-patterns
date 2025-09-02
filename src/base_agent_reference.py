# base_agent.py
"""
Base module defining an abstract agent class that all specialized agents inherit from.
This implementation is designed for AutoGen 0.6.x and provides common functionality
for all agents in the system.
"""

# Import standard Python libraries
import asyncio
import json
import traceback
import pandas as pd
from abc import ABC, abstractmethod
from typing import Any, Optional, List, Dict, Callable, Union, Awaitable

# Import the proper AutoGen core components
from autogen_core.models import (
    SystemMessage,
    UserMessage,
    AssistantMessage,
    FunctionExecutionResult,
    FunctionExecutionResultMessage
)
from autogen_agentchat.agents._assistant_agent import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core._cancellation_token import CancellationToken

# Import tool dictionary for dynamic tool access
from src.tools.tools import ALL_TOOLS
# Import only functions that are still active (minimal architecture)
from src.tools.tools import (
    fetch_unified_market_data,
)

# Yahoo functions removed - no longer used
import os
from config.config_loader import ConfigLoader

# Load configuration file for fallback values
config_loader = ConfigLoader()

# Read configuration from environment variables or fallback to config
model_name = os.getenv("OPEN_MODEL", config_loader.get("OPEN_MODEL"))
open_ai_key = os.getenv("OPEN_AI_KEY", config_loader.get("OPEN_AI_KEY"))

# Fallback map for tool execution (build dynamically to handle conditional imports)
TOOL_FUNCTION_MAP = {
    "fetch_unified_market_data": fetch_unified_market_data,
    # Minimal architecture - only essential tools
}

# Default LLM parameters
DEFAULT_LLM_CONFIG = {
    "temperature": 0.2,  # Lower temperature for more deterministic function calling
    "max_tokens": 4096,  # Ensure enough tokens for complex responses
    "top_p": 0.95,       # Focus on more likely tokens
}


class BaseAgent(AssistantAgent, ABC):
    """
    Abstract base class for AutoGen-based agents.
    Encapsulates common functionalities such as:
      - Configuration handling via AutoGen's AgentConfig
      - Memory system access for knowledge retrieval
      - Tool registration and usage
    """

    def __init__(self, name: str, tools=None, memory_system: Optional[Any] = None, llm_config: Optional[Dict[str, Any]] = None):
        """
        Initialize the agent with tools, memory system, and LLM configuration.

        :param name: Unique name/identifier for this agent.
        :param tools: List of tools the agent can use.
        :param memory_system: Optional memory interface for knowledge storage and retrieval.
        :param llm_config: Optional dictionary containing LLM settings (temperature, etc).
        """
        # 1. Merge default LLM config with any provided config
        llm_params = DEFAULT_LLM_CONFIG.copy()
        if llm_config:
            llm_params.update(llm_config)

        # 2. Create the LLM client instance for function calling
        if not open_ai_key:
            raise ValueError(
                "OpenAI API key not found. Set the OPEN_AI_KEY environment variable or update your Codex config."
            )

        client_config = {
            "model": model_name,
            "api_key": open_ai_key,
            # LLM parameters
            "temperature": llm_params.get("temperature", 0.2),
            "max_tokens": llm_params.get("max_tokens", 4096),
            "top_p": llm_params.get("top_p", 0.95),
            # API settings
            "timeout": llm_params.get("timeout", 120),
            "max_retries": llm_params.get("max_retries", 3),
        }

        model_client_instance = OpenAIChatCompletionClient(**client_config)

        # 3. Set up tools
        if tools is None:
            tools = ALL_TOOLS

        # 4. Call the parent constructor
        super().__init__(
            name=name,
            model_client=model_client_instance,
            tools=tools,
            description=f"{name} agent",
            reflect_on_tool_use=True,
            tool_call_summary_format="{result}",
        )

        # 5. Store tools in a local dict for direct access
        self._tools_dict = {tool.name: tool for tool in tools}

        # 6. Set up memory system
        self.memory_system = memory_system

        # 7. Store the LLM configuration and model client
        self.llm_config = llm_params
        self.model_client = model_client_instance

    def log(self, message: str) -> None:
        """
        Logs a message using the agent's logger or falls back to print.

        :param message: The log message.
        """
        if hasattr(self, 'logger') and self.logger:
            self.logger.info(f"[{self.name}] {message}")
        else:
            # For quick debugging, fallback to print
            print(f"[{self.name}] {message}")

    #############################
    # Message Building and Processing
    #############################

    def _build_message_sequence(self, prompt: str, system_prompt: Optional[str] = None) -> List[Any]:
        """
        Build a sequence of messages for the conversation with the LLM.

        :param prompt: The user prompt to process.
        :param system_prompt: Optional system prompt to provide context.
        :return: A list of message objects.
        """
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(UserMessage(content=prompt, source="user"))
        return messages

    def _extract_content(self, response: Any) -> str:
        """
        Extract the content from a response object.

        :param response: The response from the LLM.
        :return: The content as a string.
        """
        if not response:
            return "No response generated by the LLM."

        # Check if the response has a content attribute (AutoGen 0.5.x API)
        if hasattr(response, 'content'):
            if isinstance(response.content, str):
                return response.content
            else:
                # Not a string, convert to string (could be a list or other type)
                return str(response.content)

        # Fall back to string representation
        return str(response)

    def _parse_tool_arguments(self, tool_args: Any) -> Dict[str, Any]:
        """
        Parse tool arguments into a dictionary format that can be passed to a tool.
        This handles various formats that might be returned by the LLM.

        :param tool_args: The tool arguments in whatever format the LLM provided.
        :return: A dictionary of parsed arguments.
        """
        if isinstance(tool_args, dict):
            # Already a dictionary, just return it
            return tool_args
        elif isinstance(tool_args, str):
            # Try to parse as JSON
            try:
                parsed_args = json.loads(tool_args)
                if isinstance(parsed_args, dict):
                    return parsed_args
                else:
                    self.log(
                        f"Warning: Parsed JSON is not a dictionary: {parsed_args}")
                    return {}
            except json.JSONDecodeError:
                self.log(f"Warning: Failed to parse tool arguments as JSON")
                return {}
        else:
            # Unknown format
            self.log(
                f"Warning: Unknown tool arguments format: {type(tool_args)}")
            return {}

    #############################
    # Tool Execution
    #############################

    async def _execute_tool(self, tool_name: str, tool_args: Any) -> Any:
        """
        Core method to execute a tool with the given arguments.

        :param tool_name: The name of the tool to execute.
        :param tool_args: The arguments for the tool.
        :return: The result of the tool execution.
        """
        # Get the actual tool from the tools dict
        tool = self._tools_dict.get(tool_name)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")

        # Parse the tool arguments in a clean way
        parsed_args = self._parse_tool_arguments(tool_args)

        try:
            # Call the tool and get result
            tool_result = await self._execute_tool_async(tool, tool_name, parsed_args)

            # Log and process result
            self._log_tool_result(tool_result)
            processed_result = self.process_tool_result(
                tool_name, tool_result, parsed_args)
            return processed_result
        except Exception as e:
            traceback.print_exc()
            self.log(f"Error executing tool {tool_name}: {str(e)}")
            return f"Error executing {tool_name}: {str(e)}"

    async def _execute_tool_async(self, tool, tool_name: str, tool_args: Dict[str, Any]) -> Any:
        """
        Execute a tool asynchronously using the most appropriate method based on the tool's interface.

        :param tool: The tool object to execute
        :param tool_name: The name of the tool
        :param tool_args: The arguments to pass to the tool
        :return: The result of the tool execution
        """
        cancellation_token = CancellationToken()

        # Helper for executing a function
        async def call_exec_fn(exec_fn: Callable, *args, **kwargs) -> Any:
            """Execute a function, handling both sync and async cases."""
            if asyncio.iscoroutinefunction(exec_fn):
                self.log(f"Executing async function {exec_fn.__name__}")
                return await exec_fn(*args, **kwargs)
            else:
                self.log(
                    f"Executing sync function {exec_fn.__name__} in thread executor")
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, lambda: exec_fn(*args, **kwargs))

        # Tool access control should be handled by proper tool configuration in tools.py
        # Sentiment agents should only have access to sentiment tools via their initialization

        # Strategy 1: Use function map if available (most reliable fallback)
        if tool_name in TOOL_FUNCTION_MAP:
            try:
                exec_fn = TOOL_FUNCTION_MAP[tool_name]
                self.log(f"Executing {tool_name} via function map")
                result = await call_exec_fn(exec_fn, **tool_args)
                return result
            except Exception as e:
                self.log(f"Error executing via function map: {e}")
                # Continue to next strategy

        # Strategy 2: Direct function call if available
        if hasattr(tool, 'func') and callable(tool.func):
            try:
                self.log(f"Executing {tool_name} directly via func attribute")
                result = await call_exec_fn(tool.func, **tool_args)
                return result
            except Exception as e:
                self.log(f"Error executing via func attribute: {e}")
                # Continue to next strategy

        # Strategy 3: Call the tool directly if it's callable
        if callable(tool):
            try:
                self.log(f"Executing {tool_name} via direct call")
                result = await call_exec_fn(tool, **tool_args)
                return result
            except Exception as e:
                self.log(f"Error executing via direct call: {e}")
                # Continue to next strategy

        # Strategy 4: Use the standard run_json method (last resort)
        if hasattr(tool, 'run_json'):
            try:
                self.log(f"Executing {tool_name} via run_json")
                return await tool.run_json(tool_args, cancellation_token)
            except Exception as e:
                self.log(f"Error executing via run_json: {e}")
                # Continue to next strategy

        # If we've tried all strategies and none worked
        raise ValueError(
            f"No viable execution method found for tool: {tool_name}")

    def _log_tool_call(self, tool_name: str, tool_args: Any) -> None:
        """
        Log information about a tool call.

        :param tool_name: The name of the tool being called.
        :param tool_args: The arguments for the tool call.
        """
        if isinstance(tool_args, dict):
            args_str = ", ".join([f"{k}={v}" for k, v in tool_args.items()])
        else:
            args_str = str(tool_args)
        print(f"- LLM is using tool: {tool_name}({args_str})")

    def _log_tool_result(self, tool_result: Any) -> None:
        """
        Log information about a tool execution result.

        :param tool_result: The result from executing a tool.
        """
        if isinstance(tool_result, pd.DataFrame):
            self.log(f"Result is DataFrame with shape {tool_result.shape}")
            if not tool_result.empty:
                print(f"DataFrame head: {tool_result.head(3)}")
        else:
            self.log(f"Result is {type(tool_result)}")

    def _format_tool_result(self, result: Any, tool_name: str, tool_id: str) -> FunctionExecutionResult:
        """
        Format a tool result for use in the conversation.

        :param result: The raw or processed result from a tool.
        :param tool_name: The name of the tool that was called.
        :param tool_id: The ID of the tool call.
        :return: A FunctionExecutionResult object.
        """
        # Convert to JSON-serializable format if needed
        content_str = None

        if isinstance(result, pd.DataFrame):
            # Handle DataFrame conversion
            try:
                # Convert datetime columns to strings to avoid JSON serialization issues
                result_copy = result.copy()
                for col in result_copy.columns:
                    if result_copy[col].dtype == 'datetime64[ns]' or 'datetime' in str(result_copy[col].dtype):
                        result_copy[col] = result_copy[col].astype(str)

                result_dict = result_copy.to_dict(orient='records')
                # Add context for empty DataFrames to help LLM provide better responses
                if len(result_dict) == 0:
                    if 'Error' in result.columns and not result.empty:
                        # If we have error information, include it
                        content_str = json.dumps({
                            "data": result_dict,
                            "message": f"No data returned. DataFrame columns: {list(result.columns)}",
                            "error_info": result.to_dict('records') if not result.empty else None
                        })
                    else:
                        content_str = json.dumps({
                            "data": result_dict,
                            "message": f"No data found. Expected columns: {list(result.columns)}"
                        })
                else:
                    content_str = json.dumps(result_dict)
            except Exception as e:
                self.log(f"Error converting DataFrame to JSON: {e}")
                content_str = str(result)
        elif isinstance(result, (dict, list)):
            # Handle dict or list conversion
            try:
                content_str = json.dumps(result)
            except Exception as e:
                self.log(f"Error converting dict/list to JSON: {e}")
                content_str = str(result)
        else:
            # For strings and other types
            content_str = str(result)

        # Return in expected format
        return FunctionExecutionResult(
            content=content_str,
            call_id=tool_id,
            is_error=False,
            name=tool_name
        )

    #############################
    # Core Conversation Methods
    #############################

    async def _run_tool_conversation(self, messages: List[Any]) -> Any:
        """
        Run a conversation that may involve tool calls, but bail out after
        `self.max_tool_rounds` (default 2).  The final turn is a plain-text
        summary request with *no* tools supplied, so the model cannot call
        another function.
        """
        max_rounds = getattr(self, "max_tool_rounds", 2)
        rounds = 0
        conversation = list(messages)
        tools_list = list(self._tools_dict.values())

        while True:
            rounds += 1
            self.log(f"Calling LLM (tool round {rounds})...")
            response = await self.model_client.create(
                messages=conversation,
                tools=tools_list,
            )

            # ── If the model wants to call tools ──────────────────────
            if hasattr(response, "content") and isinstance(response.content, list):
                if rounds >= max_rounds:
                    self.log(
                        f"{self.name}: reached max_tool_rounds={max_rounds}; "
                        "stopping further tool calls."
                    )
                    break

                # record the tool call then execute it
                tool_calls = response.content
                conversation.append(
                    AssistantMessage(content=tool_calls, source="assistant")
                )
                tool_results = await self._process_tool_calls(tool_calls)
                conversation.append(
                    FunctionExecutionResultMessage(content=tool_results)
                )
                continue  # go to next round

            # ── No tool call → return assistant answer ─────────────
            return response

        # ── Ask for a text-only summary (no tools param!) ─────────────
        summary = await self.model_client.create(
            messages=conversation
            + [
                AssistantMessage(
                    content=(
                        "Summarize these findings in a final answer. "
                        "Do NOT call any more tools."
                    ),
                    source="assistant",
                )
            ]
        )
        return summary

    async def _process_tool_calls(self, tool_calls: List[Any]) -> List[FunctionExecutionResult]:
        """
        Process a list of tool calls and return their results.

        :param tool_calls: A list of tool call objects from the LLM.
        :return: A list of function execution results.
        """
        tool_results = []
        for tool_call in tool_calls:
            tool_name = tool_call.name
            tool_args = tool_call.arguments
            tool_id = tool_call.id

            # Log the tool call
            self._log_tool_call(tool_name, tool_args)

            try:
                # Execute the tool and get the result
                tool_result = await self._execute_tool(tool_name, tool_args)

                # Format the result for the LLM
                formatted_result = self._format_tool_result(
                    tool_result, tool_name, tool_id)
                tool_results.append(formatted_result)
            except Exception as e:
                # Handle tool execution errors
                error_message = f"Error executing {tool_name}: {str(e)}"
                print(error_message)
                tool_results.append(
                    FunctionExecutionResult(
                        content=error_message,
                        call_id=tool_id,
                        is_error=True,
                        name=tool_name
                    )
                )

        return tool_results

    #############################
    # Public API Methods
    #############################

    def process_with_tools(self, prompt: str, system_prompt: Optional[str] = None) -> Union[str, Awaitable[str]]:
        """
        Process a prompt with the LLM, supporting tool calling.
        This method provides the core tool calling functionality that specific agents can build upon.

        :param prompt: The user prompt to process.
        :param system_prompt: Optional system prompt to provide context.
        :return: The LLM's response or a coroutine to be awaited.
        """
        try:
            messages = self._build_message_sequence(prompt, system_prompt)
            try:
                asyncio.get_running_loop()
                in_loop = True
            except RuntimeError:
                in_loop = False

            if in_loop:
                return self.process_with_tools_async(prompt, system_prompt)
            else:
                response = asyncio.run(self._run_tool_conversation(messages))
                return self._extract_content(response)
        except Exception as e:
            error_details = traceback.format_exc()
            print(f"Error details: {error_details}")
            return f"Error processing with LLM: {str(e)}"

    async def process_with_tools_async(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Async version of process_with_tools - for use when already in an event loop.

        :param prompt: The user prompt to process.
        :param system_prompt: Optional system prompt to provide context.
        :return: The LLM's response.
        """
        try:
            messages = self._build_message_sequence(prompt, system_prompt)
            response = await self._run_tool_conversation(messages)
            return self._extract_content(response)
        except Exception as e:
            error_details = traceback.format_exc()
            print(f"Error details: {error_details}")
            return f"Error processing with LLM: {str(e)}"

    def process_tool_result(self, tool_name: str, result: Any, tool_args: Any) -> Any:
        """
        Process tool results before passing them back to the LLM.
        This is a hook for subclasses to override and add custom processing.

        :param tool_name: The name of the tool that was called.
        :param result: The raw result from the tool.
        :param tool_args: The arguments that were passed to the tool.
        :return: The processed result.
        """
        # Base implementation just returns the result without processing
        return result

    #############################
    # Memory Management Methods
    #############################

    def store_in_memory(self, key: str, data: Any) -> None:
        """
        Stores data in the memory system under the specified key.
        """
        if self.memory_system:
            self.memory_system.store_data(key, data)

    def retrieve_from_memory(self, key: str) -> Any:
        """
        Retrieves data from memory.
        """
        if self.memory_system:
            return self.memory_system.retrieve_data(key)
        return None

    def store_data_in_context(self, key: str, data: Any):
        """
        Stores data in the context layer of memory.
        """
        if self.memory_system:
            self.memory_system.store_data(key, data, layer="context")

    def retrieve_data_from_context(self, key: str):
        """
        Retrieves data from the context layer of memory.
        """
        if self.memory_system:
            return self.memory_system.retrieve_data(key, layer="context")
        return None

    def set_logger(self, logger: Any) -> None:
        """
        Attaches a logger to this agent for debugging and audit trails.

        :param logger: A logging instance (e.g., Python's built-in logging).
        """
        self.logger = logger

    @abstractmethod
    def generate_reply(self, messages, context=None) -> str:
        """
        AutoGen's required method for handling incoming messages.
        Must be implemented by all subclasses.

        :param messages: List of messages in the conversation.
        :param context: Optional context from AutoGen.
        :return: The agent's response.
        """
        pass
