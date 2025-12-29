import logging
import os

from bedrock_agentcore.memory import MemoryClient
from bedrock_agentcore.memory.constants import StrategyType
from strands.hooks import (
    AfterInvocationEvent,
    HookProvider,
    HookRegistry,
    MessageAddedEvent,
)

REGION = os.getenv("AWS_REGION")

logger = logging.getLogger(__name__)


def get_memory_config():
    """
    Get memory configuration from environment or config file.

    Returns:
        dict: Memory configuration with memory_id and region
    """
    memory_id = os.getenv("AGENTCORE_MEMORY_ID")
    if not memory_id:
        raise ValueError(
            "AGENTCORE_MEMORY_ID environment variable not set. "
            "Please run the one-time setup script first: python scripts/setup_memory.py"
        )
    return {
        "memory_id": memory_id,
        "region": REGION or "us-east-1",
    }


class CustomerSupportMemoryHooks(HookProvider):
    """Memory hooks for automated customer support memory management"""

    def __init__(
        self, memory_id: str, client: MemoryClient, actor_id: str, session_id: str
    ):
        self.memory_id = memory_id
        self.client = client
        self.actor_id = actor_id
        self.session_id = session_id

        # Get available memory strategy namespaces
        self.namespaces = {
            i["type"]: i["namespaces"][0]
            for i in self.client.get_memory_strategies(self.memory_id)
        }

    def retrieve_customer_context(self, event: MessageAddedEvent):
        """Hook 1: Retrieve customer context before processing queries"""
        messages = event.agent.messages

        # Process only user messages (not tool results)
        if (
            messages[-1]["role"] == "user"
            and "toolResult" not in messages[-1]["content"][0]
        ):
            user_query = messages[-1]["content"][0]["text"]

            try:
                all_context = []

                # Query each memory strategy namespace
                for context_type, namespace in self.namespaces.items():
                    memories = self.client.retrieve_memories(
                        memory_id=self.memory_id,
                        namespace=namespace.format(actorId=self.actor_id),
                        query=user_query,
                        top_k=3,  # Get top 3 relevant memories
                    )

                    # Format retrieved memories
                    for memory in memories:
                        if isinstance(memory, dict):
                            content = memory.get("content", {})
                            if isinstance(content, dict):
                                text = content.get("text", "").strip()
                                if text:
                                    all_context.append(
                                        f"[{context_type.upper()}] {text}"
                                    )

                # Inject context into user message
                if all_context:
                    context_text = "\n".join(all_context)
                    original_text = messages[-1]["content"][0]["text"]
                    messages[-1]["content"][0][
                        "text"
                    ] = f"Customer Context:\n{context_text}\n\n{original_text}"
                    logger.info("Retrieved %s customer context items", len(all_context))

            except Exception as e:
                logger.error("Failed to retrieve customer context: %s", e)

    def save_support_interaction(self, event: AfterInvocationEvent):
        """Hook 2: Save customer support interactions after agent responses"""
        try:
            messages = event.agent.messages

            # Ensure we have both user and assistant messages
            if len(messages) >= 2 and messages[-1]["role"] == "assistant":
                customer_query = None
                agent_response = None

                # Extract the latest conversation turn
                for msg in reversed(messages):
                    if msg["role"] == "assistant" and not agent_response:
                        agent_response = msg["content"][0]["text"]
                    elif (
                        msg["role"] == "user"
                        and not customer_query
                        and "toolResult" not in msg["content"][0]
                    ):
                        customer_query = msg["content"][0]["text"]
                        break

                # Save the interaction to memory
                if customer_query and agent_response:
                    self.client.create_event(
                        memory_id=self.memory_id,
                        actor_id=self.actor_id,
                        session_id=self.session_id,
                        messages=[
                            (customer_query, "USER"),
                            (agent_response, "ASSISTANT"),
                        ],
                    )
                    logger.info("Saved support interaction to memory")

        except Exception as e:
            logger.error("Failed to save support interaction: %s", e)

    def register_hooks(self, registry: HookRegistry) -> None:
        """Register memory hooks with the agent"""
        registry.add_callback(MessageAddedEvent, self.retrieve_customer_context)
        registry.add_callback(AfterInvocationEvent, self.save_support_interaction)
        logger.info("Customer support memory hooks registered")
