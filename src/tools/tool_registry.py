"""Tool Registry System for GEX-LLM Pattern Analysis.

Centralized tool registration, discovery, and management for multi-agent coordination. Supports dynamic tool assignment,
validation, and configuration-driven tool definitions.

Issue #152: Implement Tool Registry System for Agent Architecture
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

# AutoGen tool types for compatibility
from autogen_core.tools import FunctionTool, ToolResult, ToolSchema

from src.utils.config_manager import get_config

logger = logging.getLogger(__name__)


class AgentType(Enum):
    """Supported agent types for tool assignment."""

    DATA = "data"
    GEX = "gex"
    ANALYSIS = "analysis"
    MARKET_MECHANICS = "market_mechanics"
    VALIDATION = "validation"
    ALL = "all"


class ToolCategory(Enum):
    """Tool categories for organization and filtering."""

    DATA_RETRIEVAL = "data_retrieval"
    GEX_CALCULATION = "gex_calculation"
    PATTERN_ANALYSIS = "pattern_analysis"
    VALIDATION = "validation"
    REPORTING = "reporting"
    MARKET_INTELLIGENCE = "market_intelligence"


@dataclass
class ToolMetadata:
    """Metadata for a registered tool."""

    name: str
    description: str
    category: ToolCategory
    agent_types: List[AgentType]
    func: Callable
    requires_cache: bool = False
    requires_api: bool = False
    estimated_latency_ms: int = 100
    rate_limited: bool = False
    enabled: bool = True
    tags: List[str] = field(default_factory=list)
    version: str = "1.0.0"

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        if isinstance(other, ToolMetadata):
            return self.name == other.name
        return False


class ToolRegistry:
    """Centralized registry for tool management and discovery.

    Provides:
    - Tool registration with metadata
    - Discovery by agent type, category, or tags
    - Configuration-driven tool enablement
    - Validation of tool availability
    - Tool statistics and monitoring
    """

    _instance = None

    def __new__(cls):
        """Singleton pattern for global registry access."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the tool registry."""
        if self._initialized:
            return

        self._tools: Dict[str, ToolMetadata] = {}
        self._agent_tools: Dict[AgentType, Set[str]] = {agent: set() for agent in AgentType}
        self._category_tools: Dict[ToolCategory, Set[str]] = {cat: set() for cat in ToolCategory}
        self._tag_index: Dict[str, Set[str]] = {}

        # Load configuration
        self._config = get_config()
        self._load_config()

        self._initialized = True
        logger.info("ToolRegistry initialized")

    def _load_config(self):
        """Load tool registry configuration."""
        # Get enabled/disabled tools from config
        self._disabled_tools: Set[str] = set()
        disabled_list = self._config.get("tool_registry.disabled_tools", [])
        if isinstance(disabled_list, list):
            self._disabled_tools = set(disabled_list)

    def register(
        self,
        name: str,
        func: Callable,
        description: str,
        category: ToolCategory,
        agent_types: List[AgentType],
        requires_cache: bool = False,
        requires_api: bool = False,
        estimated_latency_ms: int = 100,
        rate_limited: bool = False,
        tags: Optional[List[str]] = None,
        version: str = "1.0.0",
    ) -> bool:
        """Register a tool with the registry.

        Args:
            name: Unique tool identifier
            func: The tool function
            description: Human-readable description
            category: Tool category for organization
            agent_types: List of agent types that can use this tool
            requires_cache: Whether tool requires cache manager
            requires_api: Whether tool requires external API access
            estimated_latency_ms: Expected execution time
            rate_limited: Whether tool is subject to rate limiting
            tags: Optional tags for filtering
            version: Tool version string

        Returns:
            True if registration successful, False if tool already exists
        """
        if name in self._tools:
            logger.warning(f"Tool '{name}' already registered, skipping")
            return False

        # Check if tool is disabled in config
        enabled = name not in self._disabled_tools

        metadata = ToolMetadata(
            name=name,
            description=description,
            category=category,
            agent_types=agent_types,
            func=func,
            requires_cache=requires_cache,
            requires_api=requires_api,
            estimated_latency_ms=estimated_latency_ms,
            rate_limited=rate_limited,
            enabled=enabled,
            tags=tags or [],
            version=version,
        )

        self._tools[name] = metadata

        # Update indices
        for agent_type in agent_types:
            self._agent_tools[agent_type].add(name)
        self._agent_tools[AgentType.ALL].add(name)

        self._category_tools[category].add(name)

        for tag in metadata.tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = set()
            self._tag_index[tag].add(name)

        logger.debug(f"Registered tool: {name} (category={category.value}, enabled={enabled})")
        return True

    def get_tool(self, name: str) -> Optional[ToolMetadata]:
        """Get a tool by name.

        Args:
            name: Tool identifier

        Returns:
            ToolMetadata if found and enabled, None otherwise
        """
        tool = self._tools.get(name)
        if tool and tool.enabled:
            return tool
        return None

    def get_tool_function(self, name: str) -> Optional[Callable]:
        """Get a tool's callable function.

        Args:
            name: Tool identifier

        Returns:
            The tool function if found and enabled, None otherwise
        """
        tool = self.get_tool(name)
        return tool.func if tool else None

    def get_tools_for_agent(self, agent_type: AgentType) -> List[ToolMetadata]:
        """Get all tools available for an agent type.

        Args:
            agent_type: The agent type to get tools for

        Returns:
            List of enabled ToolMetadata objects
        """
        tool_names = self._agent_tools.get(agent_type, set())
        return [self._tools[name] for name in tool_names if self._tools[name].enabled]

    def get_tools_by_category(self, category: ToolCategory) -> List[ToolMetadata]:
        """Get all tools in a category.

        Args:
            category: The category to filter by

        Returns:
            List of enabled ToolMetadata objects
        """
        tool_names = self._category_tools.get(category, set())
        return [self._tools[name] for name in tool_names if self._tools[name].enabled]

    def get_tools_by_tag(self, tag: str) -> List[ToolMetadata]:
        """Get all tools with a specific tag.

        Args:
            tag: The tag to filter by

        Returns:
            List of enabled ToolMetadata objects
        """
        tool_names = self._tag_index.get(tag, set())
        return [self._tools[name] for name in tool_names if self._tools[name].enabled]

    def get_tool_names_for_agent(self, agent_type: AgentType) -> List[str]:
        """Get tool names for an agent type.

        Args:
            agent_type: The agent type

        Returns:
            List of tool names
        """
        return [tool.name for tool in self.get_tools_for_agent(agent_type)]

    def enable_tool(self, name: str) -> bool:
        """Enable a tool.

        Args:
            name: Tool identifier

        Returns:
            True if tool was enabled, False if not found
        """
        if name in self._tools:
            self._tools[name].enabled = True
            logger.info(f"Enabled tool: {name}")
            return True
        return False

    def disable_tool(self, name: str) -> bool:
        """Disable a tool.

        Args:
            name: Tool identifier

        Returns:
            True if tool was disabled, False if not found
        """
        if name in self._tools:
            self._tools[name].enabled = False
            logger.info(f"Disabled tool: {name}")
            return True
        return False

    def is_tool_available(self, name: str) -> bool:
        """Check if a tool is registered and enabled.

        Args:
            name: Tool identifier

        Returns:
            True if tool exists and is enabled
        """
        tool = self._tools.get(name)
        return tool is not None and tool.enabled

    def list_all_tools(self, include_disabled: bool = False) -> List[str]:
        """List all registered tool names.

        Args:
            include_disabled: Whether to include disabled tools

        Returns:
            List of tool names
        """
        if include_disabled:
            return list(self._tools.keys())
        return [name for name, tool in self._tools.items() if tool.enabled]

    def get_registry_stats(self) -> Dict[str, Any]:
        """Get statistics about the registry.

        Returns:
            Dictionary with registry statistics
        """
        enabled_count = sum(1 for t in self._tools.values() if t.enabled)
        disabled_count = len(self._tools) - enabled_count

        category_counts = {
            cat.value: len([n for n in names if self._tools[n].enabled]) for cat, names in self._category_tools.items()
        }

        agent_counts = {
            agent.value: len([n for n in names if self._tools[n].enabled])
            for agent, names in self._agent_tools.items()
            if agent != AgentType.ALL
        }

        return {
            "total_tools": len(self._tools),
            "enabled_tools": enabled_count,
            "disabled_tools": disabled_count,
            "by_category": category_counts,
            "by_agent_type": agent_counts,
            "tags": list(self._tag_index.keys()),
        }

    def validate_tool_requirements(self, name: str, has_cache: bool = True, has_api: bool = True) -> Dict[str, Any]:
        """Validate that tool requirements are met.

        Args:
            name: Tool identifier
            has_cache: Whether cache manager is available
            has_api: Whether API access is available

        Returns:
            Dictionary with validation results
        """
        tool = self._tools.get(name)
        if not tool:
            return {"valid": False, "error": f"Tool '{name}' not found"}

        issues = []
        if tool.requires_cache and not has_cache:
            issues.append("Tool requires cache manager but none available")
        if tool.requires_api and not has_api:
            issues.append("Tool requires API access but none available")
        if not tool.enabled:
            issues.append("Tool is disabled")

        return {
            "valid": len(issues) == 0,
            "tool": name,
            "issues": issues,
            "requires_cache": tool.requires_cache,
            "requires_api": tool.requires_api,
            "rate_limited": tool.rate_limited,
        }

    def clear(self):
        """Clear all registered tools (for testing)."""
        self._tools.clear()
        self._agent_tools = {agent: set() for agent in AgentType}
        self._category_tools = {cat: set() for cat in ToolCategory}
        self._tag_index.clear()
        logger.info("ToolRegistry cleared")

    # =========================================================================
    # AutoGen Integration Methods (Quick Wins)
    # =========================================================================

    def get_function_tool(self, name: str) -> Optional[FunctionTool]:
        """Get an AutoGen FunctionTool by name.

        Args:
            name: Tool identifier

        Returns:
            AutoGen FunctionTool if found and enabled, None otherwise
        """
        tool = self.get_tool(name)
        if not tool:
            return None

        try:
            return FunctionTool(
                func=tool.func,
                name=tool.name,
                description=tool.description,
            )
        except Exception as e:
            logger.warning("Failed to create FunctionTool for %s: %s", name, e)
            return None

    def get_function_tools_for_agent(self, agent_type: AgentType) -> List[FunctionTool]:
        """Get AutoGen FunctionTools for an agent type.

        Args:
            agent_type: The agent type

        Returns:
            List of AutoGen FunctionTool objects
        """
        tools = self.get_tools_for_agent(agent_type)
        function_tools = []

        for tool_meta in tools:
            try:
                ft = FunctionTool(
                    func=tool_meta.func,
                    name=tool_meta.name,
                    description=tool_meta.description,
                )
                function_tools.append(ft)
            except Exception as e:
                logger.warning("Failed to create FunctionTool for %s: %s", tool_meta.name, e)

        return function_tools

    def get_tool_schema(self, name: str) -> Optional[ToolSchema]:
        """Get the AutoGen ToolSchema for a tool.

        Args:
            name: Tool identifier

        Returns:
            ToolSchema dict if found, None otherwise
        """
        ft = self.get_function_tool(name)
        if ft:
            return ft.schema
        return None

    def get_all_schemas(self) -> List[ToolSchema]:
        """Get schemas for all enabled tools.

        Returns:
            List of ToolSchema dicts for LLM tool calling
        """
        schemas = []
        for name in self.list_all_tools():
            schema = self.get_tool_schema(name)
            if schema:
                schemas.append(schema)
        return schemas


# Global registry instance
_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry instance.

    Returns:
        The singleton ToolRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


def register_tool(
    name: str,
    func: Callable,
    description: str,
    category: ToolCategory,
    agent_types: List[AgentType],
    **kwargs,
) -> bool:
    """Convenience function to register a tool.

    Args:
        name: Unique tool identifier
        func: The tool function
        description: Human-readable description
        category: Tool category
        agent_types: List of agent types that can use this tool
        **kwargs: Additional ToolMetadata fields

    Returns:
        True if registration successful
    """
    registry = get_tool_registry()
    return registry.register(name, func, description, category, agent_types, **kwargs)
