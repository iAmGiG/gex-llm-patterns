"""
Base Agent for GEX-LLM Pattern Analysis

Simplified agent framework focused on the specific needs of gamma exposure
analysis and LLM pattern discovery. Based on AutoGen 0.6.x architecture
but streamlined for research workflows.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime

# AutoGen core components (0.7.4)
from autogen_core.models import SystemMessage, UserMessage
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient

# Project components
from src.cache import UnifiedCacheManager
from config.config_loader import ConfigLoader
import os


class BaseGEXAgent(AssistantAgent, ABC):
    """
    Base class for GEX analysis agents.
    
    Provides common functionality for:
    - OpenAI/AutoGen integration
    - Cache management for market data
    - Logging and error handling
    - Simple tool registration
    """

    def __init__(
        self,
        name,
        description = "",
        tools= None,
        model_name = "gpt-4o-mini",
        temperature = 0.2,
        cache_manager= None
    ):
        """
        Initialize GEX agent with essential components.
        
        Args:
            name: Agent identifier
            description: Agent role description
            tools of tools agent can use
            model_name: OpenAI model (default: gpt-4o-mini for cost efficiency)
            temperature: LLM temperature for consistency
            cache_manager: Shared cache for market data
        """
        # Load configuration
        config_loader = ConfigLoader()
        api_key = os.getenv("OPENAI_API_KEY", config_loader.get("OPENAI_API_KEY"))
        
        if not api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY or update @config/")

        # Create OpenAI client with research-optimized settings
        model_client = OpenAIChatCompletionClient(
            model=model_name,
            api_key=api_key,
            temperature=temperature,
            max_tokens=4096,
            timeout=120
        )

        # Initialize parent AssistantAgent
        super().__init__(
            name=name,
            model_client=model_client,
            tools=tools or [],
            description=description or f"{name} agent for GEX analysis"
        )

        # GEX-specific components
        self.cache_manager = cache_manager or UnifiedCacheManager()
        self.logger = logging.getLogger(f"GEX.{name}")
        self.created_at = datetime.now()
        
        # Agent state
        self.processed_data = {}
        self.analysis_results = {}
        
        self.log(f"Initialized {name} agent with {len(tools or [])} tools")

    def log(self, message, level = "info") -> None:
        """Log message with agent context."""
        log_msg = f"[{self.name}] {message}"
        
        if level == "error":
            self.logger.error(log_msg)
        elif level == "warning":
            self.logger.warning(log_msg)
        else:
            self.logger.info(log_msg)

    async def process_request(self, request, context= None) -> str:
        """
        Process a request with the LLM.
        
        Args:
            request: The request/prompt to process
            context: Optional context dictionary
            
        Returns:
            LLM response as string
        """
        try:
            messages = [UserMessage(content=request, source="user")]
            
            # Add context as system message if provided
            if context:
                system_msg = self._build_context_message(context)
                messages.insert(0, SystemMessage(content=system_msg))
            
            # Get response from LLM
            response = await self.model_client.create(messages=messages, tools=self._tools)
            
            return self._extract_response_content(response)
            
        except Exception as e:
            error_msg = f"Error processing request: {str(e)}"
            self.log(error_msg, "error")
            return error_msg

    def _build_context_message(self, context) -> str:
        """Build system message from context dictionary."""
        context_parts = []
        
        if "role" in context:
            context_parts.append(f"You are a {context['role']}.")
        
        if "data_summary" in context:
            context_parts.append(f"Available data: {context['data_summary']}")
            
        if "task" in context:
            context_parts.append(f"Current task: {context['task']}")
            
        if "constraints" in context:
            context_parts.append(f"Constraints: {context['constraints']}")
            
        return " ".join(context_parts)

    def _extract_response_content(self, response: Any) -> str:
        """Extract content from LLM response."""
        if hasattr(response, 'content'):
            if isinstance(response.content, str):
                return response.content
            elif isinstance(response.content, list) and response.content:
                # Handle tool calls or multi-part content
                return str(response.content[0]) if response.content else "No response"
        
        return str(response)

    def store_data(self, key, data: Any) -> None:
        """Store data in agent's local storage."""
        self.processed_data[key] = {
            "data": data,
            "timestamp": datetime.now(),
            "agent": self.name
        }
        self.log(f"Stored data: {key}")

    def get_data(self, key) -> Any:
        """Retrieve data from agent's local storage."""
        if key in self.processed_data:
            return self.processed_data[key]["data"]
        return None

    def store_result(self, analysis_type, result: Any) -> None:
        """Store analysis results."""
        self.analysis_results[analysis_type] = {
            "result": result,
            "timestamp": datetime.now(),
            "agent": self.name
        }
        self.log(f"Stored analysis result: {analysis_type}")

    def get_result(self, analysis_type) -> Any:
        """Retrieve analysis results."""
        if analysis_type in self.analysis_results:
            return self.analysis_results[analysis_type]["result"]
        return None

    def get_status(self) :
        """Get agent status and metrics."""
        return {
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "tools_count": len(self._tools),
            "data_items": len(self.processed_data),
            "analysis_results": len(self.analysis_results),
            "cache_manager": self.cache_manager is not None
        }

    @abstractmethod
    def generate_reply(self, messages, context=None) -> str:
        """
        AutoGen required method for handling incoming messages.
        Must be implemented by subclasses.
        """
        pass


class DataCollectionAgent(BaseGEXAgent):
    """Agent specialized in collecting market data for GEX analysis."""
    
    def __init__(self, **kwargs):
        # Import tools for this agent
        from src.agents.tools import DATA_COLLECTION_TOOLS
        
        super().__init__(
            name="DataCollector",
            description="Collects SPY/SPX market data via Alpha Vantage API",
            tools=DATA_COLLECTION_TOOLS,
            **kwargs
        )

    async def generate_reply(self, messages, context=None) -> str:
        """Handle data collection requests."""
        last_message = messages[-1]["content"] if messages else ""
        
        context_dict = {
            "role": "market data collection specialist",
            "task": "collect and validate SPY/SPX options and underlying data",
            "constraints": "respect API rate limits, use caching when possible"
        }
        
        return await self.process_request(last_message, context_dict)


class GEXCalculationAgent(BaseGEXAgent):
    """Agent specialized in calculating Gamma Exposure metrics."""
    
    def __init__(self, **kwargs):
        # Import tools for this agent
        from src.agents.tools import GEX_CALCULATION_TOOLS
        
        super().__init__(
            name="GEXCalculator", 
            description="Calculates gamma exposure and related options metrics",
            tools=GEX_CALCULATION_TOOLS,
            **kwargs
        )

    async def generate_reply(self, messages, context=None) -> str:
        """Handle GEX calculation requests."""
        last_message = messages[-1]["content"] if messages else ""
        
        context_dict = {
            "role": "gamma exposure calculation specialist",
            "task": "calculate GEX levels, flip points, and gamma-weighted metrics",
            "constraints": "use Black-Scholes model, validate input data quality"
        }
        
        return await self.process_request(last_message, context_dict)


class PatternAnalysisAgent(BaseGEXAgent):
    """Agent specialized in LLM-based pattern discovery."""
    
    def __init__(self, **kwargs):
        # Import tools for this agent
        from src.agents.tools import PATTERN_ANALYSIS_TOOLS
        
        # Use GPT-4o for more complex pattern analysis
        kwargs.setdefault("model_name", "gpt-4o")
        kwargs.setdefault("temperature", 0.1)  # Lower for more consistent analysis
        
        super().__init__(
            name="PatternAnalyzer",
            description="Discovers patterns in GEX data using LLM analysis",
            tools=PATTERN_ANALYSIS_TOOLS, 
            **kwargs
        )

    async def generate_reply(self, messages, context=None) -> str:
        """Handle pattern analysis requests."""
        last_message = messages[-1]["content"] if messages else ""
        
        context_dict = {
            "role": "quantitative pattern discovery specialist",
            "task": "identify exploitable patterns in GEX and price action data",
            "constraints": "focus on statistical significance, avoid overfitting"
        }
        
        return await self.process_request(last_message, context_dict)