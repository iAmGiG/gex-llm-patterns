"""Agent Factory Pattern for GEX-LLM Agents.

Replaces direct inheritance with factory-based agent creation.
Issue #153: Replace Base Agent Inheritance with Factory Pattern.

Benefits:
- Centralized agent creation and configuration
- Easy to add new agent types without modifying base classes
- Better testability through dependency injection
- Integration with ToolRegistry for tool assignment
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type

from src.utils.config_manager import get_config

logger = logging.getLogger(__name__)


class AgentType(Enum):
    """Available agent types in the system."""

    DATA_COLLECTION = "data_collection"
    GEX_CALCULATION = "gex_calculation"
    PATTERN_ANALYSIS = "pattern_analysis"
    MARKET_MECHANICS = "market_mechanics"
    DATA_RETRIEVAL = "data_retrieval"
    VALIDATION = "validation"


@dataclass
class AgentConfig:
    """Configuration for agent creation."""

    agent_type: AgentType
    name: str
    description: str = ""
    model_name: str = "gpt-4o-mini"
    temperature: float = 0.2
    max_tokens: int = 4096
    timeout: int = 120
    tools: List[str] = field(default_factory=list)
    extra_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentInstance:
    """Wrapper for created agent instances with metadata."""

    agent: Any
    config: AgentConfig
    agent_type: AgentType
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            from src.utils.date_utils import now_iso

            self.created_at = now_iso()


class AgentFactory:
    """Factory for creating GEX-LLM agents.

    Centralizes agent creation with:
    - Configuration-driven defaults
    - Tool registry integration
    - Consistent initialization patterns
    """

    _instance: Optional["AgentFactory"] = None
    _creators: Dict[AgentType, Callable] = {}

    def __new__(cls):
        """Singleton pattern for factory."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the factory with default creators."""
        if self._initialized:
            return

        self._config = get_config()
        self._agent_configs: Dict[AgentType, AgentConfig] = {}
        self._created_agents: List[AgentInstance] = []

        # Register default creators
        self._register_default_creators()
        self._load_config_defaults()
        self._initialized = True

        logger.info("AgentFactory initialized")

    def _register_default_creators(self):
        """Register default agent creator functions."""
        # Lazy import to avoid circular dependencies
        self._creators = {
            AgentType.DATA_COLLECTION: self._create_data_collection_agent,
            AgentType.GEX_CALCULATION: self._create_gex_calculation_agent,
            AgentType.PATTERN_ANALYSIS: self._create_pattern_analysis_agent,
            AgentType.MARKET_MECHANICS: self._create_market_mechanics_agent,
            AgentType.DATA_RETRIEVAL: self._create_data_retrieval_agent,
            AgentType.VALIDATION: self._create_validation_agent,
        }

    def _load_config_defaults(self):
        """Load default configurations from YAML."""
        try:
            factory_config = self._config.get("agent_factory.factory", {})

            for agent_type in AgentType:
                type_key = agent_type.value
                type_config = factory_config.get(type_key, {})

                self._agent_configs[agent_type] = AgentConfig(
                    agent_type=agent_type,
                    name=type_config.get("name", f"{type_key}_agent"),
                    description=type_config.get("description", f"Agent for {type_key}"),
                    model_name=type_config.get(
                        "model_name",
                        self._config.get("agent_factory.base_agent.default_model", "gpt-4o-mini"),
                    ),
                    temperature=type_config.get(
                        "temperature",
                        self._config.get("agent_factory.base_agent.default_temperature", 0.2),
                    ),
                    max_tokens=type_config.get(
                        "max_tokens",
                        self._config.get("agent_factory.base_agent.max_tokens", 4096),
                    ),
                    timeout=type_config.get(
                        "timeout",
                        self._config.get("agent_factory.base_agent.timeout_seconds", 120),
                    ),
                    tools=type_config.get("tools", []),
                    extra_config=type_config.get("extra", {}),
                )

            logger.info(f"Loaded config defaults for {len(self._agent_configs)} agent types")
        except Exception as e:
            logger.warning(f"Failed to load factory config: {e}. Using defaults.")

    def register_creator(self, agent_type: AgentType, creator: Callable[[AgentConfig], Any]) -> None:
        """Register a custom creator function for an agent type.

        Args:
            agent_type: The type of agent
            creator: Function that takes AgentConfig and returns an agent instance
        """
        self._creators[agent_type] = creator
        logger.info(f"Registered custom creator for {agent_type.value}")

    def create(
        self,
        agent_type: AgentType,
        config_override: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> AgentInstance:
        """Create an agent of the specified type.

        Args:
            agent_type: Type of agent to create
            config_override: Optional config values to override defaults
            **kwargs: Additional arguments passed to agent constructor

        Returns:
            AgentInstance wrapping the created agent
        """
        if agent_type not in self._creators:
            raise ValueError(f"No creator registered for agent type: {agent_type}")

        # Get base config
        base_config = self._agent_configs.get(agent_type, AgentConfig(agent_type=agent_type, name=agent_type.value))

        # Apply overrides
        if config_override:
            config = self._merge_config(base_config, config_override)
        else:
            config = base_config

        # Merge kwargs into extra_config
        if kwargs:
            config.extra_config.update(kwargs)

        # Create the agent
        try:
            creator = self._creators[agent_type]
            agent = creator(config)

            instance = AgentInstance(agent=agent, config=config, agent_type=agent_type)
            self._created_agents.append(instance)

            logger.info(f"Created {agent_type.value} agent: {config.name}")
            return instance

        except Exception as e:
            logger.error(f"Failed to create {agent_type.value} agent: {e}")
            raise

    def _merge_config(self, base: AgentConfig, overrides: Dict[str, Any]) -> AgentConfig:
        """Merge override values into base config."""
        return AgentConfig(
            agent_type=base.agent_type,
            name=overrides.get("name", base.name),
            description=overrides.get("description", base.description),
            model_name=overrides.get("model_name", base.model_name),
            temperature=overrides.get("temperature", base.temperature),
            max_tokens=overrides.get("max_tokens", base.max_tokens),
            timeout=overrides.get("timeout", base.timeout),
            tools=overrides.get("tools", base.tools),
            extra_config={**base.extra_config, **overrides.get("extra_config", {})},
        )

    # --- Agent Creator Methods ---

    def _create_data_collection_agent(self, config: AgentConfig) -> Any:
        """Create a DataCollectionAgent."""
        from src.base_agent import DataCollectionAgent

        return DataCollectionAgent(
            model_name=config.model_name,
            temperature=config.temperature,
        )

    def _create_gex_calculation_agent(self, config: AgentConfig) -> Any:
        """Create a GEXCalculationAgent."""
        from src.base_agent import GEXCalculationAgent

        return GEXCalculationAgent(
            model_name=config.model_name,
            temperature=config.temperature,
        )

    def _create_pattern_analysis_agent(self, config: AgentConfig) -> Any:
        """Create a PatternAnalysisAgent."""
        from src.base_agent import PatternAnalysisAgent

        return PatternAnalysisAgent(
            model_name=config.model_name,
            temperature=config.temperature,
        )

    def _create_market_mechanics_agent(self, config: AgentConfig) -> Any:
        """Create a MarketMechanicsAgent."""
        from src.agents.market_mechanics_agent import MarketMechanicsAgent

        return MarketMechanicsAgent(
            symbol=config.extra_config.get("symbol", "SPY"),
            config=config.extra_config.get("agent_config"),
        )

    def _create_data_retrieval_agent(self, config: AgentConfig) -> Any:
        """Create a DataRetrievalAgent."""
        from src.agents.data_retrieval_agent import DataRetrievalAgent

        return DataRetrievalAgent(
            data_source=config.extra_config.get("data_source", "production"),
            validate=config.extra_config.get("validate", True),
            enable_sample_fallback=config.extra_config.get("enable_sample_fallback", True),
        )

    def _create_validation_agent(self, config: AgentConfig) -> Any:
        """Create a validation agent (placeholder for future implementation)."""
        # For now, return a MarketMechanicsAgent configured for validation
        from src.agents.market_mechanics_agent import MarketMechanicsAgent

        return MarketMechanicsAgent(
            symbol=config.extra_config.get("symbol", "SPY"),
            config=config.extra_config.get("agent_config"),
        )

    # --- Utility Methods ---

    def get_config(self, agent_type: AgentType) -> AgentConfig:
        """Get the current configuration for an agent type."""
        return self._agent_configs.get(agent_type, AgentConfig(agent_type=agent_type, name=agent_type.value))

    def set_config(self, agent_type: AgentType, config: AgentConfig) -> None:
        """Set configuration for an agent type."""
        self._agent_configs[agent_type] = config
        logger.info(f"Updated config for {agent_type.value}")

    def get_created_agents(self) -> List[AgentInstance]:
        """Get list of all agents created by this factory."""
        return self._created_agents.copy()

    def get_agent_types(self) -> List[AgentType]:
        """Get list of available agent types."""
        return list(self._creators.keys())

    def clear_created_agents(self) -> None:
        """Clear the list of created agents (for testing)."""
        self._created_agents.clear()

    def get_factory_stats(self) -> Dict[str, Any]:
        """Get statistics about the factory."""
        type_counts = {}
        for instance in self._created_agents:
            type_name = instance.agent_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1

        return {
            "total_agents_created": len(self._created_agents),
            "registered_types": [t.value for t in self._creators.keys()],
            "agents_by_type": type_counts,
        }


# Module-level convenience functions
_factory: Optional[AgentFactory] = None


def get_agent_factory() -> AgentFactory:
    """Get the singleton AgentFactory instance."""
    global _factory
    if _factory is None:
        _factory = AgentFactory()
    return _factory


def create_agent(
    agent_type: AgentType,
    config_override: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> AgentInstance:
    """Convenience function to create an agent.

    Args:
        agent_type: Type of agent to create
        config_override: Optional config overrides
        **kwargs: Additional arguments

    Returns:
        AgentInstance wrapping the created agent
    """
    return get_agent_factory().create(agent_type, config_override, **kwargs)


def create_market_mechanics_agent(symbol: str = "SPY", config: Optional[Dict] = None) -> AgentInstance:
    """Convenience function to create a MarketMechanicsAgent.

    Args:
        symbol: Trading symbol
        config: Optional agent configuration

    Returns:
        AgentInstance wrapping the MarketMechanicsAgent
    """
    return create_agent(
        AgentType.MARKET_MECHANICS,
        config_override={"extra_config": {"symbol": symbol, "agent_config": config}},
    )


def create_data_retrieval_agent(
    data_source: str = "production",
    validate: bool = True,
    enable_sample_fallback: bool = True,
) -> AgentInstance:
    """Convenience function to create a DataRetrievalAgent.

    Args:
        data_source: Data source type
        validate: Enable data validation
        enable_sample_fallback: Enable sample data fallback

    Returns:
        AgentInstance wrapping the DataRetrievalAgent
    """
    return create_agent(
        AgentType.DATA_RETRIEVAL,
        config_override={
            "extra_config": {
                "data_source": data_source,
                "validate": validate,
                "enable_sample_fallback": enable_sample_fallback,
            }
        },
    )
