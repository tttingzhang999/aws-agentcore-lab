import os
import uuid

from bedrock_agentcore.memory import MemoryClient
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from dotenv import load_dotenv
from mcp_client.client import get_streamable_http_mcp_client
from memory.client import CustomerSupportMemoryHooks, get_memory_config
from model.load import load_model
from strands import Agent
from strands_tools.code_interpreter import AgentCoreCodeInterpreter
from tools.add_numbers import add_numbers
from tools.get_product_info import get_product_info
from tools.get_return_policy import get_return_policy
from tools.get_technical_support import get_technical_support
from tools.web_search import web_search

# 加載 .env 文件（本地測試時使用）
load_dotenv()

app = BedrockAgentCoreApp()
log = app.logger

REGION = os.getenv("AWS_REGION", "ap-northeast-1")

# Import AgentCore Gateway as Streamable HTTP MCP Client
mcp_client = get_streamable_http_mcp_client()

# system prompt
system_prompt = """You are a helpful and professional customer support assistant for an e-commerce company.
Your role is to:
- Provide accurate information using the tools available to you
- Be friendly, patient, and understanding with customers
- Always offer additional help after answering questions
- If you can't help with something, direct customers to the appropriate contact

You have access to the following tools:
1. get_return_policy() - For return policy questions
2. get_product_info() - To get information about a specific product
3. web_search() - Search the web for troubleshooting help

Always use the appropriate tool to get accurate, up-to-date information rather than guessing.
Always use traditional chinese to response"""


@app.entrypoint
async def invoke(payload, context):
    """
    Main entrypoint for the customer support agent with memory capabilities.

    This agent uses AgentCore Memory to:
    - Remember customer preferences and history
    - Provide personalized responses based on past interactions
    - Automatically save new interactions for future context
    """
    session_id = getattr(context, "session_id", str(uuid.uuid4()))

    # Get customer identifier from payload or context (default to session for demo)
    customer_id = payload.get("customer_id", getattr(context, "actor_id", session_id))

    # Create code interpreter
    code_interpreter = AgentCoreCodeInterpreter(
        region=REGION, session_name=session_id, auto_create=True, persist_sessions=True
    )

    # Initialize memory client and configuration
    try:
        memory_config = get_memory_config()
        memory_client = MemoryClient(region_name=REGION)

        # Create memory hooks for automatic context management
        memory_hooks = CustomerSupportMemoryHooks(
            memory_id=memory_config["memory_id"],
            client=memory_client,
            actor_id=customer_id,
            session_id=session_id,
        )
        log.info(
            f"Memory hooks initialized for customer {customer_id}, session {session_id}"
        )
    except ValueError as e:
        log.warning(f"Memory not configured: {e}")
        log.warning("Agent will run without memory capabilities")
        memory_hooks = None

    with mcp_client as client:
        # Get MCP Tools
        tools = client.list_tools_sync()

        # Create agent with memory hooks (if configured)
        agent_kwargs = {
            "model": load_model(),
            "system_prompt": system_prompt,
            "tools": [
                code_interpreter.code_interpreter,
                add_numbers,
                get_return_policy,
                get_product_info,
                web_search,
                get_technical_support,
            ]
            + tools,
        }

        # Add memory hooks if available
        if memory_hooks:
            agent_kwargs["hooks"] = [memory_hooks]

        agent = Agent(**agent_kwargs)

        # Execute and format response
        stream = agent.stream_async(payload.get("prompt"))

        async for event in stream:
            # Handle Text parts of the response
            if "data" in event and isinstance(event["data"], str):
                yield event["data"]

            # Implement additional handling for other events
            # if "toolUse" in event:
            #   # Process toolUse

            # Handle end of stream
            # if "result" in event:
            #    yield(format_response(event["result"]))


def format_response(result) -> str:
    """Extract code from metrics and format with LLM response."""
    parts = []

    # Extract executed code from metrics
    try:
        tool_metrics = result.metrics.tool_metrics.get("code_interpreter")
        if tool_metrics and hasattr(tool_metrics, "tool"):
            action = tool_metrics.tool["input"]["code_interpreter_input"]["action"]
            if "code" in action:
                parts.append(
                    f"## Executed Code:\n```{action.get('language', 'python')}\n{action['code']}\n```\n---\n"
                )
    except (AttributeError, KeyError):
        pass  # No code to extract

    # Add LLM response
    parts.append(f"## 📊 Result:\n{str(result)}")
    return "\n".join(parts)


if __name__ == "__main__":
    app.run()
