import os

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from mcp_client.client import get_streamable_http_mcp_client
from model.load import load_model
from strands import Agent
from strands_tools.code_interpreter import AgentCoreCodeInterpreter
from tools.add_numbers import add_numbers
from tools.get_product_info import get_product_info
from tools.get_return_policy import get_return_policy
from tools.get_technical_support import get_technical_support
from tools.web_search import web_search

app = BedrockAgentCoreApp()
log = app.logger

REGION = os.getenv("AWS_REGION")

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

Always use the appropriate tool to get accurate, up-to-date information rather than guessing."""


@app.entrypoint
async def invoke(payload, context):
    session_id = getattr(context, "session_id", "default")

    # Create code interpreter
    code_interpreter = AgentCoreCodeInterpreter(
        region=REGION, session_name=session_id, auto_create=True, persist_sessions=True
    )

    with mcp_client as client:
        # Get MCP Tools
        tools = client.list_tools_sync()

        # Create agent
        agent = Agent(
            model=load_model(),
            system_prompt=system_prompt,
            tools=[
                code_interpreter.code_interpreter,
                add_numbers,
                get_return_policy,
                get_product_info,
                web_search,
                get_technical_support,
            ]
            + tools,
        )

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
