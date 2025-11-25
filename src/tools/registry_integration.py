"""Registry Integration for Existing AutoGen Tools.

Bridges the existing autogen_tools.py with the new ToolRegistry system. Provides backward compatibility while enabling
new registry features.

Issue #152: Implement Tool Registry System for Agent Architecture
"""

import logging
from typing import List, Optional

from autogen_core.tools import FunctionTool

from src.tools.tool_registry import AgentType, ToolCategory, ToolMetadata, get_tool_registry, register_tool

logger = logging.getLogger(__name__)


def register_existing_tools():
    """Register all existing tools from autogen_tools.py with the registry.

    This function bridges the legacy tool definitions with the new registry system. Call this during application startup
    to populate the registry.
    """
    # Import existing tools lazily to avoid circular imports
    from src.tools import autogen_tools

    registry = get_tool_registry()

    # Track registration results
    registered = 0
    skipped = 0

    # Register data retrieval tools
    data_tools = [
        (
            "fetch_options_data",
            autogen_tools.fetch_options_data,
            ToolCategory.DATA_RETRIEVAL,
            [AgentType.DATA, AgentType.ANALYSIS],
            True,
            True,
            True,
            500,
            ["options", "alpha_vantage", "cache"],
        ),
        (
            "fetch_market_data",
            autogen_tools.fetch_market_data,
            ToolCategory.DATA_RETRIEVAL,
            [AgentType.DATA, AgentType.ANALYSIS],
            True,
            True,
            True,
            300,
            ["market", "polygon", "cache"],
        ),
        (
            "query_analysis",
            autogen_tools.query_analysis,
            ToolCategory.MARKET_INTELLIGENCE,
            [AgentType.DATA, AgentType.ANALYSIS, AgentType.MARKET_MECHANICS],
            False,
            False,
            False,
            50,
            ["query", "intelligence"],
        ),
        (
            "algo_time_analysis",
            autogen_tools.algo_time_analysis,
            ToolCategory.DATA_RETRIEVAL,
            [AgentType.DATA, AgentType.ANALYSIS, AgentType.MARKET_MECHANICS],
            True,
            False,
            False,
            100,
            ["intraday", "algo", "timing"],
        ),
    ]

    # Register GEX calculation tools
    gex_tools = [
        (
            "calculate_gamma_exposure",
            autogen_tools.calculate_gamma_exposure,
            ToolCategory.GEX_CALCULATION,
            [AgentType.GEX, AgentType.ANALYSIS, AgentType.MARKET_MECHANICS],
            True,
            False,
            False,
            200,
            ["gex", "gamma", "calculation"],
        ),
        (
            "find_flip_points",
            autogen_tools.find_flip_points,
            ToolCategory.GEX_CALCULATION,
            [AgentType.GEX, AgentType.ANALYSIS, AgentType.MARKET_MECHANICS],
            True,
            False,
            False,
            150,
            ["gex", "flip_point", "dealer"],
        ),
        (
            "process_historical_gex_range",
            autogen_tools.process_historical_gex_range,
            ToolCategory.GEX_CALCULATION,
            [AgentType.GEX, AgentType.ANALYSIS],
            True,
            True,
            True,
            5000,
            ["gex", "historical", "batch"],
        ),
    ]

    # Register analysis tools
    analysis_tools = [
        (
            "technical_confluence",
            autogen_tools.analyze_technical_confluence,
            ToolCategory.PATTERN_ANALYSIS,
            [AgentType.ANALYSIS, AgentType.MARKET_MECHANICS],
            True,
            False,
            False,
            300,
            ["pattern", "technical", "confluence"],
        ),
    ]

    # Combine all tools
    all_tool_defs = data_tools + gex_tools + analysis_tools

    for tool_def in all_tool_defs:
        name, func, category, agent_types, requires_cache, requires_api, rate_limited, latency, tags = tool_def

        # Get description from the function's docstring or use a default
        description = func.__doc__.split("\n")[0] if func.__doc__ else f"Tool: {name}"

        success = register_tool(
            name=name,
            func=func,
            description=description,
            category=category,
            agent_types=agent_types,
            requires_cache=requires_cache,
            requires_api=requires_api,
            rate_limited=rate_limited,
            estimated_latency_ms=latency,
            tags=tags,
        )

        if success:
            registered += 1
        else:
            skipped += 1

    logger.info(f"Tool registration complete: {registered} registered, {skipped} skipped")
    return {"registered": registered, "skipped": skipped}


def get_autogen_tools_for_agent(agent_type: str) -> List[FunctionTool]:
    """Get AutoGen FunctionTool objects for an agent type.

    This provides backward compatibility with existing agent initialization.

    Args:
        agent_type: Agent type string (e.g., 'data', 'gex', 'analysis')

    Returns:
        List of AutoGen FunctionTool objects
    """
    # Map string to AgentType enum
    type_map = {
        "data": AgentType.DATA,
        "gex": AgentType.GEX,
        "analysis": AgentType.ANALYSIS,
        "market_mechanics": AgentType.MARKET_MECHANICS,
        "validation": AgentType.VALIDATION,
    }

    agent_enum = type_map.get(agent_type.lower(), AgentType.ALL)
    registry = get_tool_registry()
    tools = registry.get_tools_for_agent(agent_enum)

    # Convert to AutoGen FunctionTool objects
    autogen_tools = []
    for tool_meta in tools:
        try:
            func_tool = FunctionTool(
                func=tool_meta.func,
                name=tool_meta.name,
                description=tool_meta.description,
            )
            autogen_tools.append(func_tool)
        except Exception as e:
            logger.warning(f"Failed to create FunctionTool for {tool_meta.name}: {e}")

    return autogen_tools


def get_tool_by_name(name: str) -> Optional[FunctionTool]:
    """Get a single AutoGen FunctionTool by name.

    Args:
        name: Tool name

    Returns:
        FunctionTool if found and enabled, None otherwise
    """
    registry = get_tool_registry()
    tool_meta = registry.get_tool(name)

    if not tool_meta:
        return None

    try:
        return FunctionTool(
            func=tool_meta.func,
            name=tool_meta.name,
            description=tool_meta.description,
        )
    except Exception as e:
        logger.warning(f"Failed to create FunctionTool for {name}: {e}")
        return None


def validate_agent_tools(agent_type: str, has_cache: bool = True, has_api: bool = True) -> dict:
    """Validate that all tools for an agent type are available.

    Args:
        agent_type: Agent type string
        has_cache: Whether cache manager is available
        has_api: Whether API access is available

    Returns:
        Dictionary with validation results
    """
    type_map = {
        "data": AgentType.DATA,
        "gex": AgentType.GEX,
        "analysis": AgentType.ANALYSIS,
        "market_mechanics": AgentType.MARKET_MECHANICS,
        "validation": AgentType.VALIDATION,
    }

    agent_enum = type_map.get(agent_type.lower(), AgentType.ALL)
    registry = get_tool_registry()

    tools = registry.get_tools_for_agent(agent_enum)
    results = {
        "agent_type": agent_type,
        "total_tools": len(tools),
        "valid_tools": 0,
        "invalid_tools": 0,
        "issues": [],
    }

    for tool in tools:
        validation = registry.validate_tool_requirements(tool.name, has_cache, has_api)
        if validation["valid"]:
            results["valid_tools"] += 1
        else:
            results["invalid_tools"] += 1
            results["issues"].append(
                {
                    "tool": tool.name,
                    "issues": validation["issues"],
                }
            )

    results["all_valid"] = results["invalid_tools"] == 0
    return results


# Convenience function for initialization
def initialize_tool_registry():
    """Initialize the tool registry with all existing tools.

    Call this during application startup.
    """
    logger.info("Initializing tool registry...")
    result = register_existing_tools()
    stats = get_tool_registry().get_registry_stats()
    logger.info(f"Tool registry initialized: {stats}")
    return result
