"""Agent Communication Bus for Multi-Agent Coordination.

Implements Issue #154: Pub-Sub message bus for inter-agent communication.

Enables:
- Parallel agent execution
- Result sharing between agents
- Coordinated multi-asset analysis
- Async event-driven workflows
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from src.utils.config_manager import get_config

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Standard event types for agent communication."""

    DATA_FETCHED = "data_fetched"
    GEX_CALCULATED = "gex_calculated"
    PATTERNS_DETECTED = "patterns_detected"
    ANALYSIS_COMPLETE = "analysis_complete"
    ERROR = "error"
    CUSTOM = "custom"


@dataclass
class AgentMessage:
    """Message passed between agents via the bus.

    Attributes:
        source_agent: ID of the agent sending the message
        event_type: Type of event (from EventType enum or custom string)
        payload: Data payload of the message
        timestamp: When the message was created
        correlation_id: Optional ID to correlate related messages
        priority: Message priority (higher = more urgent)
        ttl_seconds: Time-to-live before message expires
    """

    source_agent: str
    event_type: Union[EventType, str]
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = None
    priority: int = 0
    ttl_seconds: Optional[int] = None
    message_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def is_expired(self) -> bool:
        """Check if message has expired based on TTL."""
        if self.ttl_seconds is None:
            return False
        elapsed = (datetime.now() - self.timestamp).total_seconds()
        return elapsed > self.ttl_seconds

    def get_event_key(self) -> str:
        """Get standardized event key."""
        if isinstance(self.event_type, EventType):
            return self.event_type.value
        return str(self.event_type)


@dataclass
class Subscription:
    """Represents a subscription to events."""

    subscriber_id: str
    event_type: Union[EventType, str]
    callback: Callable[[AgentMessage], Any]
    filter_source: Optional[str] = None  # Only receive from specific source


class AgentBus:
    """Pub-Sub message bus for inter-agent communication.

    Features:
    - Subscribe to specific event types
    - Publish messages with automatic delivery
    - Wait for specific results with timeout
    - Gather multiple results in parallel
    - Message history and replay capability
    """

    _instance: Optional["AgentBus"] = None

    def __new__(cls):
        """Singleton pattern for global bus access."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the message bus."""
        if self._initialized:
            return

        self._config = get_config()
        self._subscriptions: Dict[str, List[Subscription]] = {}
        self._results: Dict[str, AgentMessage] = {}
        self._pending: Dict[str, asyncio.Event] = {}
        self._message_history: List[AgentMessage] = []
        self._max_history = self._config.get("agent_bus.max_history", 1000)
        self._default_timeout = self._config.get("agent_bus.default_timeout", 30.0)
        self._initialized = True

        logger.info("AgentBus initialized")

    def subscribe(
        self,
        subscriber_id: str,
        event_type: Union[EventType, str],
        callback: Callable[[AgentMessage], Any],
        filter_source: Optional[str] = None,
    ) -> str:
        """Subscribe to events of a specific type.

        Args:
            subscriber_id: ID of the subscribing agent
            event_type: Type of event to subscribe to
            callback: Function to call when event is received
            filter_source: Only receive from specific source agent

        Returns:
            Subscription key for later unsubscription
        """
        event_key = event_type.value if isinstance(event_type, EventType) else event_type

        if event_key not in self._subscriptions:
            self._subscriptions[event_key] = []

        subscription = Subscription(
            subscriber_id=subscriber_id,
            event_type=event_type,
            callback=callback,
            filter_source=filter_source,
        )

        self._subscriptions[event_key].append(subscription)
        subscription_key = f"{subscriber_id}:{event_key}"

        logger.debug(f"Subscription added: {subscription_key}")
        return subscription_key

    def unsubscribe(self, subscriber_id: str, event_type: Union[EventType, str]) -> bool:
        """Unsubscribe from events.

        Args:
            subscriber_id: ID of the subscriber
            event_type: Event type to unsubscribe from

        Returns:
            True if subscription was found and removed
        """
        event_key = event_type.value if isinstance(event_type, EventType) else event_type

        if event_key not in self._subscriptions:
            return False

        original_count = len(self._subscriptions[event_key])
        self._subscriptions[event_key] = [
            sub for sub in self._subscriptions[event_key] if sub.subscriber_id != subscriber_id
        ]

        removed = len(self._subscriptions[event_key]) < original_count
        if removed:
            logger.debug(f"Unsubscribed {subscriber_id} from {event_key}")

        return removed

    async def publish(self, message: AgentMessage) -> int:
        """Publish a message to the bus.

        Args:
            message: The message to publish

        Returns:
            Number of subscribers notified
        """
        if message.is_expired():
            logger.warning(f"Message {message.message_id} already expired, not publishing")
            return 0

        event_key = message.get_event_key()
        result_key = f"{message.source_agent}:{event_key}"

        # Store result for direct retrieval
        self._results[result_key] = message

        # Add to history
        self._message_history.append(message)
        if len(self._message_history) > self._max_history:
            self._message_history = self._message_history[-self._max_history :]

        # Notify subscribers
        notified = 0
        subscriptions = self._subscriptions.get(event_key, [])

        for subscription in subscriptions:
            # Apply source filter
            if subscription.filter_source and subscription.filter_source != message.source_agent:
                continue

            try:
                result = subscription.callback(message)
                # Handle async callbacks
                if asyncio.iscoroutine(result):
                    await result
                notified += 1
            except Exception as e:
                logger.error(f"Callback error for {subscription.subscriber_id}: {e}")

        # Signal waiters
        if result_key in self._pending:
            self._pending[result_key].set()

        logger.debug(f"Published {event_key} from {message.source_agent}, notified {notified}")
        return notified

    def publish_sync(self, message: AgentMessage) -> int:
        """Synchronous publish (creates event loop if needed).

        Args:
            message: The message to publish

        Returns:
            Number of subscribers notified
        """
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context, use create_task
            future = asyncio.ensure_future(self.publish(message))
            return 0  # Can't wait synchronously in async context
        except RuntimeError:
            # No running loop, create one
            return asyncio.run(self.publish(message))

    async def wait_for_result(
        self,
        source_agent: str,
        event_type: Union[EventType, str],
        timeout: Optional[float] = None,
    ) -> Optional[AgentMessage]:
        """Wait for a specific agent's result.

        Args:
            source_agent: ID of the agent to wait for
            event_type: Type of event to wait for
            timeout: Seconds to wait (None uses default)

        Returns:
            The message if received, None on timeout
        """
        event_key = event_type.value if isinstance(event_type, EventType) else event_type
        result_key = f"{source_agent}:{event_key}"
        timeout = timeout or self._default_timeout

        # Check if already available
        if result_key in self._results:
            msg = self._results[result_key]
            if not msg.is_expired():
                return msg

        # Create event if not exists
        if result_key not in self._pending:
            self._pending[result_key] = asyncio.Event()
        else:
            # Reset for new wait
            self._pending[result_key].clear()

        try:
            await asyncio.wait_for(self._pending[result_key].wait(), timeout=timeout)
            return self._results.get(result_key)
        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for {result_key}")
            return None

    async def gather_results(
        self,
        queries: List[tuple],
        timeout: Optional[float] = None,
    ) -> Dict[str, Optional[AgentMessage]]:
        """Wait for multiple agent results in parallel.

        Args:
            queries: List of (source_agent, event_type) tuples
            timeout: Seconds to wait for all results

        Returns:
            Dictionary mapping result keys to messages
        """
        timeout = timeout or self._default_timeout * 2

        tasks = [self.wait_for_result(agent, event_type, timeout) for agent, event_type in queries]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        return {
            f"{q[0]}:{q[1].value if isinstance(q[1], EventType) else q[1]}": (
                r if not isinstance(r, Exception) else None
            )
            for q, r in zip(queries, results)
        }

    def get_result(self, source_agent: str, event_type: Union[EventType, str]) -> Optional[AgentMessage]:
        """Get a stored result without waiting.

        Args:
            source_agent: ID of the source agent
            event_type: Type of event

        Returns:
            The stored message or None
        """
        event_key = event_type.value if isinstance(event_type, EventType) else event_type
        result_key = f"{source_agent}:{event_key}"
        msg = self._results.get(result_key)

        if msg and msg.is_expired():
            del self._results[result_key]
            return None

        return msg

    def get_history(
        self,
        event_type: Optional[Union[EventType, str]] = None,
        source_agent: Optional[str] = None,
        limit: int = 100,
    ) -> List[AgentMessage]:
        """Get message history with optional filters.

        Args:
            event_type: Filter by event type
            source_agent: Filter by source agent
            limit: Maximum messages to return

        Returns:
            List of matching messages (newest first)
        """
        messages = self._message_history.copy()
        messages.reverse()  # Newest first

        if event_type:
            event_key = event_type.value if isinstance(event_type, EventType) else event_type
            messages = [m for m in messages if m.get_event_key() == event_key]

        if source_agent:
            messages = [m for m in messages if m.source_agent == source_agent]

        return messages[:limit]

    def clear_results(self, older_than_seconds: Optional[int] = None) -> int:
        """Clear stored results.

        Args:
            older_than_seconds: Only clear results older than this

        Returns:
            Number of results cleared
        """
        if older_than_seconds is None:
            count = len(self._results)
            self._results.clear()
            return count

        cutoff = datetime.now()
        to_remove = []

        for key, msg in self._results.items():
            elapsed = (cutoff - msg.timestamp).total_seconds()
            if elapsed > older_than_seconds:
                to_remove.append(key)

        for key in to_remove:
            del self._results[key]

        return len(to_remove)

    def get_stats(self) -> Dict[str, Any]:
        """Get bus statistics.

        Returns:
            Dictionary with bus statistics
        """
        subscription_counts = {k: len(v) for k, v in self._subscriptions.items()}

        return {
            "total_subscriptions": sum(subscription_counts.values()),
            "subscriptions_by_event": subscription_counts,
            "stored_results": len(self._results),
            "history_size": len(self._message_history),
            "pending_waits": len(self._pending),
        }

    def reset(self) -> None:
        """Reset the bus (for testing)."""
        self._subscriptions.clear()
        self._results.clear()
        self._pending.clear()
        self._message_history.clear()
        logger.info("AgentBus reset")


# Module-level convenience functions
_bus: Optional[AgentBus] = None


def get_agent_bus() -> AgentBus:
    """Get the singleton AgentBus instance."""
    global _bus
    if _bus is None:
        _bus = AgentBus()
    return _bus


def create_message(
    source_agent: str,
    event_type: Union[EventType, str],
    payload: Dict[str, Any],
    correlation_id: Optional[str] = None,
    priority: int = 0,
    ttl_seconds: Optional[int] = None,
) -> AgentMessage:
    """Convenience function to create a message.

    Args:
        source_agent: ID of the sending agent
        event_type: Type of event
        payload: Message data
        correlation_id: Optional correlation ID
        priority: Message priority
        ttl_seconds: Optional time-to-live

    Returns:
        New AgentMessage instance
    """
    return AgentMessage(
        source_agent=source_agent,
        event_type=event_type,
        payload=payload,
        correlation_id=correlation_id,
        priority=priority,
        ttl_seconds=ttl_seconds,
    )


async def publish_result(
    source_agent: str,
    event_type: Union[EventType, str],
    payload: Dict[str, Any],
    **kwargs,
) -> int:
    """Convenience function to publish a result.

    Args:
        source_agent: ID of the sending agent
        event_type: Type of event
        payload: Message data
        **kwargs: Additional message parameters

    Returns:
        Number of subscribers notified
    """
    message = create_message(source_agent, event_type, payload, **kwargs)
    return await get_agent_bus().publish(message)
