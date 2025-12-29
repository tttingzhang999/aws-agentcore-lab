"""
本地測試腳本 - 測試 Agent 和工具（含 Gateway MCP 工具）

使用方式:
    python test_agent_local.py
"""

import asyncio
import os
import uuid

import httpx
from bedrock_agentcore.memory import MemoryClient
from dotenv import load_dotenv
from mcp.client.streamable_http import streamable_http_client
from memory.client import CustomerSupportMemoryHooks, get_memory_config
from model.load import load_model
from strands import Agent
from strands.tools.mcp import MCPClient
from tools.add_numbers import add_numbers
from tools.get_product_info import get_product_info
from tools.get_return_policy import get_return_policy
from tools.get_technical_support import get_technical_support
from utils.aws_helpers import get_or_create_cognito_pool, get_ssm_parameter

# 加載 .env 文件
load_dotenv()


# 固定的測試客戶 ID - 確保跨 session 記憶
REGION = os.getenv("AWS_REGION", "ap-northeast-1")
TEST_CUSTOMER_ID = os.getenv("TEST_CUSTOMER_ID", "test_customer_001")

# System prompt
system_prompt = """You are a helpful and professional customer support assistant for an e-commerce company.
Your role is to:
- Provide accurate information using the tools available to you
- Be friendly, patient, and understanding with customers
- Always offer additional help after answering questions
- If you can't help with something, direct customers to the appropriate contact

You have access to tools for:
- Product information and return policies
- Warranty status checking
- Technical support and troubleshooting
- Web search for latest information

When a customer asks about warranty status, use the warranty checking tool.
When a customer needs troubleshooting help, you can search the web for solutions.
Always use the appropriate tool to get accurate, up-to-date information rather than guessing.
Always use traditional chinese to response"""


def get_gateway_mcp_client():
    """Get MCP client for AgentCore Gateway."""
    try:
        # Get Gateway URL from SSM
        gateway_url = get_ssm_parameter("/app/customersupport/agentcore/gateway_url")

        if not gateway_url:
            print("⚠️  Gateway URL not found in SSM")
            print("   Run: python scripts/setup_gateway.py")
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

        print("✅ Gateway MCP client created")
        return mcp_client

    except Exception as e:
        print(f"⚠️  Failed to create Gateway client: {e}")
        print("   Agent will run with local tools only")
        return None


def create_agent_with_memory():
    """創建帶有 memory 功能的 Agent（含 Gateway MCP 工具）"""
    import logging

    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
    logging.getLogger("memory.client").setLevel(logging.INFO)
    logging.getLogger("bedrock_agentcore.memory").setLevel(logging.INFO)
    logging.getLogger("strands").setLevel(logging.WARNING)

    # Define local tools
    local_tools = [
        add_numbers,
        get_return_policy,
        get_product_info,
        get_technical_support,
    ]

    # Get Gateway MCP client
    print("\n🌐 Connecting to AgentCore Gateway...")
    mcp_client = get_gateway_mcp_client()

    # Return mcp_client without closing it - caller will manage context
    # Gateway tools will be added when MCP client context is active

    print(f"\n📊 Agent Configuration:")
    print(f"   Total tools: {len(local_tools)} local tools")
    if mcp_client:
        print(f"   Gateway MCP client: Ready ✅")
        print(f"   (Gateway tools will be loaded in MCP context)")
    else:
        print(f"   Gateway MCP client: Not available ⚠️")

    # Initialize Memory
    memory_hooks = None
    session_id = str(uuid.uuid4())

    try:
        memory_config = get_memory_config()
        memory_client = MemoryClient(region_name=REGION)

        memory_hooks = CustomerSupportMemoryHooks(
            memory_id=memory_config["memory_id"],
            client=memory_client,
            actor_id=TEST_CUSTOMER_ID,
            session_id=session_id,
        )
        print("   Memory: Enabled ✅")
        print(f"   - Customer ID: {TEST_CUSTOMER_ID}")
        print(f"   - Memory ID: {memory_config['memory_id']}")
        print(f"   - Session ID: {session_id}")
    except ValueError as e:
        print(f"   Memory: Disabled ⚠️ ({e})")
    except Exception as e:
        print(f"   Memory: Error ❌ ({e})")

    # Create agent with local tools only
    # Gateway tools will be added dynamically in MCP client context
    agent_kwargs = {
        "model": load_model(),
        "system_prompt": system_prompt,
        "tools": local_tools,
    }

    if memory_hooks:
        agent_kwargs["hooks"] = [memory_hooks]

    agent = Agent(**agent_kwargs)

    return agent, session_id, mcp_client, local_tools


def test_tools():
    """測試本地工具函式"""
    print("\n" + "=" * 80)
    print("🧪 測試 1: 本地工具函式")
    print("=" * 80)

    # Test 1: get_return_policy
    print("\n📋 Test 1.1: get_return_policy('smartphones')")
    print("-" * 80)
    result = get_return_policy("smartphones")
    print(result)

    # Test 2: get_product_info
    print("\n📦 Test 1.2: get_product_info('Samsung Galaxy S22')")
    print("-" * 80)
    result = get_product_info("Samsung Galaxy S22")
    print(result)

    # Test 3: get_technical_support
    print("\n🔧 Test 1.3: get_technical_support('phone won\\'t turn on')")
    print("-" * 80)
    result = get_technical_support("phone won't turn on")
    print(result)

    # Test 4: add_numbers
    print("\n🔢 Test 1.4: add_numbers(123, 456)")
    print("-" * 80)
    result = add_numbers(123, 456)
    print(f"Result: {result}")

    print("\n🌐 Gateway MCP Tools (check_warranty_status, web_search)")
    print("-" * 80)
    print("These tools are loaded from AgentCore Gateway at runtime.")
    print("Test them in interactive mode with:")
    print("  - 'Check warranty for serial MNO33333333'")
    print("  - 'Search web for iPhone 14 battery tips'")


def test_agent_with_memory():
    """測試 Agent 對話（with Memory & Gateway tools）"""
    print("\n" + "=" * 80)
    print("🧠 測試 2: Agent 對話 (with Memory & Gateway tools)")
    print("=" * 80)

    agent, _session_id, mcp_client, local_tools = create_agent_with_memory()

    test_prompts = [
        "我想了解 iPhone 14 的退貨政策",
        "幫我查詢保固狀態，序號是 MNO33333333",  # Gateway MCP tool
        "搜尋一下 MacBook Pro 過熱的解決方案",  # Gateway MCP tool
    ]

    # Use MCP client context if available
    if mcp_client:
        with mcp_client:
            # Load Gateway tools within context
            try:
                gateway_tools = mcp_client.list_tools_sync()
                all_tools = local_tools + gateway_tools
                agent.tools = all_tools
                print(f"\n✅ Loaded {len(gateway_tools)} Gateway tools")
            except Exception as e:
                print(f"\n⚠️  Failed to load Gateway tools: {e}")

            for i, prompt in enumerate(test_prompts, 1):
                print(f"\n📝 Test 2.{i}: {prompt}")
                print("-" * 80)
                try:
                    response = agent(prompt)
                    print(f"🤖 Response: {response}")
                except Exception as e:
                    print(f"❌ Error: {e}")
    else:
        # No MCP client, run without Gateway tools
        for i, prompt in enumerate(test_prompts, 1):
            print(f"\n📝 Test 2.{i}: {prompt}")
            print("-" * 80)
            try:
                response = agent(prompt)
                print(f"🤖 Response: {response}")
            except Exception as e:
                print(f"❌ Error: {e}")


async def test_agent_streaming():
    """測試 Agent 串流回應（with Memory & Gateway tools）"""
    print("\n" + "=" * 80)
    print("📡 測試 3: Agent 串流回應 (with Memory & Gateway tools)")
    print("=" * 80)

    agent, _session_id, mcp_client, local_tools = create_agent_with_memory()

    prompt = "幫我查保固狀態，序號 MNO33333333，並搜尋這個產品的使用評價"

    print(f"\n📝 Prompt: {prompt}")
    print("-" * 80)
    print("🤖 Response (streaming):")

    try:
        if mcp_client:
            with mcp_client:
                # Load Gateway tools within context
                try:
                    gateway_tools = mcp_client.list_tools_sync()
                    all_tools = local_tools + gateway_tools
                    agent.tools = all_tools
                    print(f"\n✅ Loaded {len(gateway_tools)} Gateway tools\n")
                except Exception as e:
                    print(f"\n⚠️  Failed to load Gateway tools: {e}\n")

                stream = agent.stream_async(prompt)
                async for chunk in stream:
                    if "data" in chunk and isinstance(chunk["data"], str):
                        print(chunk["data"], end="", flush=True)
                print()  # New line after streaming
        else:
            stream = agent.stream_async(prompt)
            async for chunk in stream:
                if "data" in chunk and isinstance(chunk["data"], str):
                    print(chunk["data"], end="", flush=True)
            print()  # New line after streaming
    except Exception as e:
        print(f"\n❌ Error: {e}")


async def interactive_mode():
    """互動模式 - 可以持續與 Agent 對話（含 Gateway tools）"""
    print("\n" + "=" * 80)
    print("💬 互動模式 - 與 Agent 對話")
    print("=" * 80)
    print("輸入 'quit' 或 'exit' 離開\n")

    # Get MCP client and local tools (don't create agent yet)
    _, session_id, mcp_client, local_tools = create_agent_with_memory()
    print("-" * 80)

    # Setup memory hooks
    memory_hooks = None
    try:
        memory_config = get_memory_config()
        memory_client = MemoryClient(region_name=REGION)
        memory_hooks = CustomerSupportMemoryHooks(
            memory_id=memory_config["memory_id"],
            client=memory_client,
            actor_id=TEST_CUSTOMER_ID,
            session_id=session_id,
        )
    except Exception:
        pass  # Already logged in create_agent_with_memory

    conversation_count = 0

    # Interactive loop function
    async def run_interactive_loop(agent):
        """Run the interactive loop with the agent."""
        nonlocal conversation_count

        while True:
            try:
                user_input = input("\n👤 你: ").strip()

                if user_input.lower() in ["quit", "exit", "bye"]:
                    print("\n👋 再見！")
                    break

                if not user_input:
                    continue

                conversation_count += 1
                print(f"\n🤖 Agent (#{conversation_count}):")
                print("-" * 80)

                try:
                    # Use streaming for better UX
                    stream = agent.stream_async(user_input)
                    async for _ in stream:
                        pass
                    print()  # New line after streaming
                except Exception as e:
                    print(f"❌ Error: {e}")
                    import traceback
                    traceback.print_exc()

            except KeyboardInterrupt:
                print("\n\n👋 再見！")
                break
            except EOFError:
                print("\n\n👋 再見！")
                break

    # Create and run agent within MCP context (following Jupyter notebook pattern)
    if mcp_client:
        with mcp_client:
            # Load Gateway tools within MCP context
            try:
                gateway_tools = mcp_client.list_tools_sync()
                all_tools = local_tools + gateway_tools
                print(f"\n✅ Loaded {len(gateway_tools)} Gateway tools")
                for tool in gateway_tools:
                    print(f"   - {tool.tool_name}")
                print(
                    f"   Total tools: {len(all_tools)} ({len(local_tools)} local + {len(gateway_tools)} gateway)"
                )
            except Exception as e:
                print(f"\n⚠️  Failed to load Gateway tools: {e}")
                print(f"   Using {len(local_tools)} local tools only")
                all_tools = local_tools
                import traceback
                traceback.print_exc()

            # Create agent INSIDE MCP context with all tools (key fix!)
            agent_kwargs = {
                "model": load_model(),
                "system_prompt": system_prompt,
                "tools": all_tools,  # ← Tools included at creation time
            }
            if memory_hooks:
                agent_kwargs["hooks"] = [memory_hooks]

            agent = Agent(**agent_kwargs)
            print("\n✅ Agent created with all tools inside MCP context")

            # Run interactive loop while in MCP context
            await run_interactive_loop(agent)
    else:
        # No MCP client - create agent with local tools only
        print(f"\n   Using {len(local_tools)} local tools only")
        agent_kwargs = {
            "model": load_model(),
            "system_prompt": system_prompt,
            "tools": local_tools,
        }
        if memory_hooks:
            agent_kwargs["hooks"] = [memory_hooks]

        agent = Agent(**agent_kwargs)
        await run_interactive_loop(agent)


def main():
    """主選單"""
    print("\n" + "=" * 80)
    print("🎯 AgentCore Customer Support Agent - 本地測試")
    print("=" * 80)
    print("\n選擇測試模式:\n")
    print("1. 測試工具函式（本地工具）")
    print("2. 測試 Agent 對話 (with Memory & Gateway tools)")
    print("3. 測試 Agent 串流回應 (with Memory & Gateway tools)")
    print("4. 互動模式 (與 Agent 對話)")
    print("5. 執行所有測試\n")

    choice = input("請選擇 (1-5): ").strip()

    if choice == "1":
        test_tools()
    elif choice == "2":
        test_agent_with_memory()
    elif choice == "3":
        asyncio.run(test_agent_streaming())
    elif choice == "4":
        asyncio.run(interactive_mode())
    elif choice == "5":
        test_tools()
        test_agent_with_memory()
        asyncio.run(test_agent_streaming())
        print("\n所有自動測試完成！按 Enter 進入互動模式...")
        input()
        asyncio.run(interactive_mode())
    else:
        print("❌ 無效的選擇")


if __name__ == "__main__":
    main()
