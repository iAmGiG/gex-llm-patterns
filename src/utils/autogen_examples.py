"""
Clean Tools Configuration for RH2MAS
Active tools: Google Search (news), Polygon.io (primary market data), Alpha Vantage (fallback)
"""

# Standard library imports
import logging
import pandas as pd

# Third-party imports
from autogen_core.tools import FunctionTool

# Project imports - only tools actually used
from src.tools.data_sources.market.unified_market_tool import fetch_unified_market_data
from src.tools.data_sources.market.vxx_volatility_tool import fetch_vxx_volatility_data
from src.tools.data_sources.market.market_context_tool import market_context_tool
from src.tools.data_sources.news.google_search_simple import google_search_smart_tool, set_news_governor
from src.tools.data_sources.news.hierarchical_news_tool import fetch_hierarchical_news

logger = logging.getLogger(__name__)

##################################
# Agent Types
##################################

SENTIMENT_AGENT = "sentiment"
TECH_AGENT = "tech"
STRATEGY_AGENT = "strategy"
ALL_AGENTS = [SENTIMENT_AGENT, TECH_AGENT, STRATEGY_AGENT]

# Note: Individual Alpha Vantage and hierarchical market data tools removed
# All market data access now handled by unified_market_tool for consistency

# Note: Direct Polygon.io tool removed - functionality handled by unified_market_tool
# with proper caching and fallback management

# Unified market data tool using cache adapter
unified_market_tool = FunctionTool(
    func=fetch_unified_market_data,
    name="fetch_unified_market_data",
    description="Fetch market data using unified cache system. Routes through cache adapter for consistent data management across Polygon and Alpha Vantage sources."
)
unified_market_tool.agent_types = [TECH_AGENT]

##################################
# VXX Volatility Tool for V2 Sentiment
##################################

vxx_volatility_tool = FunctionTool(
    func=fetch_vxx_volatility_data,
    name="fetch_vxx_volatility_data",
    description="Fetch VXX volatility data for market fear-based sentiment analysis. Returns VXX-based sentiment scores for V2 Market Fear sentiment agent."
)
vxx_volatility_tool.agent_types = [SENTIMENT_AGENT]

##################################
# Hierarchical News Tool for V4 Sentiment
##################################

hierarchical_news_tool = FunctionTool(
    func=fetch_hierarchical_news,
    name="fetch_hierarchical_news",
    description="Fetch hierarchical adaptive news mix for V4 sentiment analysis. Provides balanced company-specific, sector ETF, and broad market news for intelligent sentiment reasoning."
)
hierarchical_news_tool.agent_types = [SENTIMENT_AGENT]

##################################
# Tool Collections by Agent Type
##################################

# SENTIMENT_AGENT tools - Multiple approaches for V0-V4 framework
# V1: Google Search + smart sampling, V2: VXX volatility, V4: Hierarchical news
_sentiment_tools_raw = [
    google_search_smart_tool,   # V1: Google Custom Search API with smart sampling
    vxx_volatility_tool,        # V2: VXX volatility data for market fear sentiment
    hierarchical_news_tool,     # V4: Hierarchical adaptive news (Direct + Sector + Market)
    market_context_tool,        # V4: SPY/QQQ market context for enhanced sentiment
]
SENTIMENT_TOOLS = [tool for tool in _sentiment_tools_raw if tool is not None]

# TECH_AGENT tools - Unified market data with cache adapter routing
_tech_tools_raw = [
    # Primary: Unified tool with cache adapter (routes Polygon -> Alpha Vantage)
    unified_market_tool,
    # Note: Individual polygon/alpha_vantage tools removed - redundant with unified tool
]
TECH_TOOLS = [tool for tool in _tech_tools_raw if tool is not None]

# STRATEGY_AGENT tools - Strategy aggregates outputs from other agents
_strategy_tools_raw = [
    # Strategy agent aggregates results from other agents
    # No direct data access tools needed
]
STRATEGY_TOOLS = [tool for tool in _strategy_tools_raw if tool is not None]

# All tools combined (filter out None values from conditional imports)
ALL_TOOLS = list(set(
    tool for tool in (
        SENTIMENT_TOOLS +
        TECH_TOOLS +
        STRATEGY_TOOLS
    ) if tool is not None
))

# Tool dispatcher dictionary for efficient lookup by name
ALL_TOOLS_DICT = {tool.name: tool for tool in ALL_TOOLS if tool is not None}

##################################
# Helper function to get tools for a specific agent type
##################################


def get_tools_for_agent(agent_type):
    """
    Get the list of tools that should be used by a specific agent type.

    Args:
        agent_type: Type of agent (e.g., 'sentiment', 'tech', 'strategy')

    Returns:
        List of FunctionTool objects appropriate for the agent type
    """
    if agent_type == SENTIMENT_AGENT:
        return SENTIMENT_TOOLS
    elif agent_type == TECH_AGENT:
        return TECH_TOOLS
    elif agent_type == STRATEGY_AGENT:
        return STRATEGY_TOOLS  # Strategy agent aggregates, no direct tools needed
    else:
        # Return all tools if agent type is unknown
        return ALL_TOOLS


##################################
# NewsGovernor Integration
##################################

def enable_smart_news_sampling(governor=None):
    """
    Enable smart news sampling across all sentiment agents.

    Args:
        governor: NewsGovernor instance, or None for balanced default
    """
    from src.tools.news_governor import create_balanced_governor

    if governor is None:
        governor = create_balanced_governor()

    set_news_governor(governor)

    return governor


def disable_smart_news_sampling():
    """Disable smart news sampling (revert to direct API calls)."""
    set_news_governor(None)


def get_news_quota_status():
    """Get current news quota status if NewsGovernor is enabled."""
    from src.tools.data_sources.news.google_search_simple import _news_governor

    if _news_governor is not None:
        return _news_governor.get_quota_status()
    else:
        return {"status": "disabled", "message": "NewsGovernor not enabled"}
