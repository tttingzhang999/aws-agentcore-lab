import os
import uuid

import httpx
from bedrock_agentcore.memory import MemoryClient
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from dotenv import load_dotenv
from mcp.client.streamable_http import streamable_http_client
from memory.client import CustomerSupportMemoryHooks, get_memory_config
from model.load import load_model
from strands import Agent
from strands.tools.mcp import MCPClient
from strands_tools.code_interpreter import AgentCoreCodeInterpreter
from tools.add_numbers import add_numbers
from tools.get_product_info import get_product_info
from tools.get_return_policy import get_return_policy
from tools.get_technical_support import get_technical_support
from utils.aws_helpers import get_or_create_cognito_pool, get_ssm_parameter

# 加載 .env 文件（本地測試時使用）
load_dotenv()

app = BedrockAgentCoreApp()
log = app.logger

REGION = os.getenv("AWS_REGION", "ap-northeast-1")

# system prompt
system_prompt = """You are a helpful and professional customer support assistant for an e-commerce company.
Your role is to:
- Provide accurate information using the tools available to you
- Be friendly, patient, and understanding with customers
- Always offer additional help after answering questions
- If you can't help with something, direct customers to the appropriate contact

You have access to the following tools:

Local Tools:
1. get_return_policy() - For return policy questions
2. get_product_info(product_id) - To get detailed information about a specific product
3. get_technical_support(query) - Get technical support information and troubleshooting steps
4. code_interpreter - Execute Python code for calculations and data analysis

Gateway MCP Tools (note the full tool name with prefix):
5. CustomerSupportLambdaTools___check_warranty_status(serial_number, customer_email) - Check warranty status using product serial number
6. CustomerSupportLambdaTools___web_search(keywords, region, max_results) - Search the web for information and troubleshooting help

Important guidelines:
- For WARRANTY queries, ALWAYS use CustomerSupportLambdaTools___check_warranty_status tool with the product serial number
- For TECHNICAL issues or troubleshooting, use get_technical_support tool
- For PRODUCT information, use get_product_info tool
- For general web searches, use CustomerSupportLambdaTools___web_search tool
- Always use the appropriate tool to get accurate, up-to-date information rather than guessing

Always use traditional chinese to response
"""


def get_mcp_client():
    """
    Get MCP client connected to AgentCore Gateway.

    Returns:
        MCPClient configured with Gateway URL and authentication
    """
    try:
        # Get Gateway URL from SSM
        gateway_url = get_ssm_parameter("/app/customersupport/agentcore/gateway_url")

        if not gateway_url:
            log.warning("Gateway URL not found in SSM, MCP tools will not be available")
            return None

        # Create transport callable that gets fresh token each time
        def create_transport():
            # Get fresh Cognito authentication token
            cognito_config = get_or_create_cognito_pool(refresh_token=True)
            bearer_token = cognito_config["bearer_token"]

            # Create httpx client with authentication headers
            http_client = httpx.AsyncClient(
                headers={"Authorization": f"Bearer {bearer_token}"},
                timeout=30.0,
            )

            return streamable_http_client(gateway_url, http_client=http_client)

        # Create MCP client with authenticated HTTP client
        mcp_client = MCPClient(create_transport)

        log.info(f"MCP client connected to Gateway: {gateway_url}")
        return mcp_client

    except Exception as e:
        log.error(f"Failed to create MCP client: {e}")
        return None


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

    # Get MCP client for Gateway tools
    mcp_client = get_mcp_client()

    # Define local tools (product-specific tools)
    local_tools = [
        code_interpreter.code_interpreter,
        add_numbers,
        get_return_policy,
        get_product_info,
        get_technical_support,
    ]

    # Add Gateway MCP tools if available
    all_tools = local_tools
    if mcp_client:
        try:
            with mcp_client as client:
                # Get MCP Tools from Gateway (check_warranty_status, web_search)
                gateway_tools = client.list_tools_sync()
                all_tools = local_tools + gateway_tools
                log.info(f"Added {len(gateway_tools)} tools from Gateway")
        except Exception as e:
            log.warning(f"Failed to get Gateway tools, using local tools only: {e}")

    # Create agent with memory hooks (if configured)
    agent_kwargs = {
        "model": load_model(),
        "system_prompt": system_prompt,
        "tools": all_tools,
    }

    # Add memory hooks if available
    if memory_hooks:
        agent_kwargs["hooks"] = [memory_hooks]

    agent = Agent(**agent_kwargs)

    # Execute and format response
    if mcp_client:
        with mcp_client:
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
    else:
        stream = agent.stream_async(payload.get("prompt"))
        async for event in stream:
            # Handle Text parts of the response
            if "data" in event and isinstance(event["data"], str):
                yield event["data"]


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
